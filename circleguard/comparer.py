import itertools
import sys
import logging
import math

import numpy as np
from scipy import signal, stats

from circleguard.loadable import Replay
from circleguard.enums import Mod
from circleguard.exceptions import InvalidArgumentsException, CircleguardException
import circleguard.utils as utils
from circleguard.result import StealResult

class Comparer:
    """
    Manages comparing :class:`~.replay.Replay`\s for replay stealing.

    Parameters
    ----------
    replays1: list[:class:`~circleguard.loadable.Replay`]
        The replays to compare against either ``replays2`` if ``replays2`` is
        not ``None``, or against other replays in ``replays1``.
    replays2: list[:class:`~circleguard.loadable.Replay`]
        The replays to compare against ``replays1``.

    Notes
    -----
    If ``replays2`` is passed, each replay in ``replays1`` is compared against
    each replay in ``replays2``. Otherwise, each replay in ``replays1`` is
    compared against each other replay in ``replays1``
    (``len(replays1) choose 2`` comparisons).

    The order of ``replays1`` and ``replays2`` has no effect; comparing 1 to 2
    is the same as comparing 2 to 1.

    See Also
    --------
    :class:`~circleguard.investigator.Investigator`, for investigating single
    replays.
    """

    def __init__(self, replays1, replays2=None):
        self.log = logging.getLogger(__name__)

        # filter beatmaps we had no data for
        self.replays1 = [replay for replay in replays1 if replay.replay_data is not None]
        self.replays2 = [replay for replay in replays2 if replay.replay_data is not None] if replays2 else None
        self.mode = "double" if self.replays2 else "single"
        self.log.debug("Comparer initialized: %r", self)

    def compare(self):
        """
        If ``replays2`` is not ``None``, compares all replays in replays1
        against all replays in replays2. Otherwise, compares all replays in
        ``replays1`` against all other replays in ``replays1``
        (``len(replays1) choose 2`` comparisons).

        Yields
        ------
        :class:`~.result.ComparisonResult`
            Results representing the comparison of two replays.
        """

        self.log.info("Comparing replays with mode: %s", self.mode)
        self.log.debug("replays1: %r", self.replays1)
        self.log.debug("replays2: %r", self.replays2)

        #TODO: a little bit hacky and I don't think works 100% correctly, if mode is double but replays2 is None
        if not self.replays1 or self.replays2 == []:
            return

        if self.mode == "double":
            iterator = itertools.product(self.replays1, self.replays2)
        elif self.mode == "single":
            iterator = itertools.combinations(self.replays1, 2)
        else:
            raise InvalidArgumentsException("'mode' must be one of 'double' or 'single'")

        for replay1, replay2 in iterator:
            if replay1.replay_id == replay2.replay_id:
                self.log.debug("Not comparing %r and %r with the same id", replay1, replay2)
                continue
            yield self._result(replay1, replay2)


    def _result(self, replay1, replay2):
        """
        Compares two :class:`~.replay.Replay`\s.

        Parameters
        ----------
        replay1: :class:`~.replay.Replay`
            The first replay to compare.
        replay2: :class:`~.replay.Replay`
            The second replay to compare.

        Returns
        -------
        :class:`~.result.ComparisonResult`
            The result of comparing ``replay1`` to ``replay2``.
        """
        self.log.log(utils.TRACE, "comparing %r and %r", replay1, replay2)
        (mean, correlation) = Comparer._compare_two_replays(replay1, replay2)
        return StealResult(replay1, replay2, mean, correlation)

    @staticmethod
    def _compare_two_replays(replay1, replay2, num_chunks=20):
        """
        Calculates the average cursor distance between two
        :class:`~.replay.Replay`\s, and the standard deviation of the distance.

        Parameters
        ----------
        replay1: :class:`~.replay.Replay`
            The first replay to compare.
        replay2: :class:`~.replay.Replay`
            The second replay to compare.

        Returns
        -------
        (float, float)
            The mean distance of the cursors of the two replays.
            Also returns a correlation metric that represents the median level of correlation in the replay.
        """

        # interpolate
        if len(replay1.t) > len(replay2.t):
            xy1 = np.array(replay1.xy)  # implicit fast copy to avoid overwriting this array on replay1 when flipping for HR

            xy2x = np.interp(replay1.t, replay2.t, replay2.xy[:, 0])
            xy2y = np.interp(replay1.t, replay2.t, replay2.xy[:, 1])
            xy2 = np.array([xy2x, xy2y]).T
        else:
            xy1x = np.interp(replay2.t, replay1.t, replay1.xy[:, 0])
            xy1y = np.interp(replay2.t, replay1.t, replay1.xy[:, 1])
            xy1 = np.array([xy1x, xy1y]).T

            xy2 = np.array(replay2.xy)  # implicit fast copy to avoid overwriting this array on replay2 when flipping for HR

        valid = np.all(([0, 0] <= xy1) & (xy1 <= [512, 384]), axis=1) & np.all(([0, 0] <= xy2) & (xy2 <= [512, 384]), axis=1)
        xy1 = xy1[valid]
        xy2 = xy2[valid]

        # flip if one but not both has HR
        if (Mod.HR in replay1.mods) ^ (Mod.HR in replay2.mods):
            xy1[:, 1] = 384 - xy1[:, 1]

        play_sequence_1 = xy1.T.copy() # Need copy, as the cross_correlate method uses an in-place modification of the matrix
        play_sequence_2 = xy2.T.copy()

        # Sectioned into 20 chunks, used to ignore outliers (eg. long replay with breaks is copied, and the cheater cursordances during the break)
        horizontal_length = play_sequence_1.shape[1] - play_sequence_1.shape[1] % num_chunks
        play_sequence_1_sections = np.hsplit(play_sequence_1[:,:horizontal_length], num_chunks)
        play_sequence_2_sections = np.hsplit(play_sequence_2[:,:horizontal_length], num_chunks)
        correlations = []
        for (play_sequence_1, play_sequence_2) in zip(play_sequence_1_sections, play_sequence_2_sections):
            cross_correlation_matrix = Comparer.find_cross_correlation(play_sequence_1, play_sequence_2)
            #Pick the lag with the maximum correlation, this likely in most cases is 0 lag
            max_correlation = max(cross_correlation_matrix.reshape(cross_correlation_matrix.size))
            correlations.append(max_correlation)
        average_distance = Comparer._compute_data_similarity(xy1, xy2)
        # Out of all the sections, we should have 20 sections, we pick the one with the median correlation, so we throw away any outliers
        median_correlation = np.median(np.array(sorted(correlations)))
        return (average_distance, median_correlation)

    @staticmethod
    def find_cross_correlation(play_sequence_1, play_sequence_2):
        # The normalization makes the similarity detector robust to translations
        play_sequence_1 -= np.mean(play_sequence_1)
        play_sequence_2 -= np.mean(play_sequence_2)
        norm = np.std(play_sequence_1) * np.std(play_sequence_2) * play_sequence_1.size
        return signal.correlate(play_sequence_1, play_sequence_2) / norm


    @staticmethod
    def _compute_data_similarity(data1, data2):
        """
        Calculates the average cursor distance between two lists of cursor data,
        and the standard deviation of the distance.

        Parameters
        ----------
        data1: list[tuple(int, int)]
            The first set of cursor data, containing the x and y positions
            of the cursor at each datapoint.
        data2: list[tuple(int, int)]
            The second set of cursor data, containing the x and y positions
            of the cursor at each datapoint.

        Returns
        -------
        float
            The average distance between the two datasets.

        Notes
        -----
        The two data lists must have previously been interpolated to each other.
        This is why we can get away with only lists of [x,y] and not [x,y,t].
        """

        data1 = np.array(data1)
        data2 = np.array(data2)

        # switch if the second is longer, so that data1 is always the longest.
        if len(data2) > len(data1):
            (data1, data2) = (data2, data1)

        shortest = len(data2)

        distance = data1[:shortest] - data2
        # square all numbers and sum over the second axis (add row 2 to row 1),
        # finally take the square root of each number to get all distances.
        # [ x_1 x_2 ... x_n   => [ x_1 ** 2 ... x_n ** 2
        #   y_1 y_2 ... y_n ] =>   y_1 ** 2 ... y_n ** 2 ]
        # => [ x_1 ** 2 + y_1 ** 2 ... x_n ** 2 + y_n ** 2 ]
        # => [ d_1 ... d_2 ]
        distance = (distance ** 2).sum(axis=1) ** 0.5

        return distance.mean()

    def __repr__(self):
        return f"Comparer(replays1={self.replays1},replays2={self.replays2})"

    def __str__(self):
        return f"Comparer with {len(self.replays1)} and {len(self.replays2)} replays"
