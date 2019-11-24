import itertools
import sys
import logging
import math

import numpy as np
import itertools as itr

from circleguard.replay import Replay, ReplayModified
from circleguard.enums import Mod, CleanMode
from circleguard.exceptions import InvalidArgumentsException, CircleguardException
import circleguard.utils as utils
from circleguard.result import ReplayStealingResult

class Comparer:
    """
    Manages comparing :class:`~.replay.Replay`\s for replay stealing.

    Parameters
    ----------
    detect: :class:`~.Detect`
        Information on how to prepare for comparison and the steal threshold.
        If a comparison scores below this value, one of the
        :class:`~.replay.Replay` in the comparison is considered cheated.
    replays1: list[:class:`~.replay.Replay`]
        The replays to compare against either ``replays2`` if ``replays`` is
        not ``None``, or against other replays in ``replays1``.
    replays2: list[:class:`~.replay.Replay`]
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
    :class:`~investigator.Investigator`, for investigating single replays.
    """

    def __init__(self, detect, replays1, replays2=None):
        self.log = logging.getLogger(__name__)
        self.detect = detect

        # filter beatmaps we had no data for - see Loader.replay_data and OnlineReplay.from_map
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

        if self.mode == "single" and self.detect.clean_mode.value:
            self.replays1 = ReplayModified.clean_set(self.replays1, self.detect.clean_mode)

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

        if CleanMode.SEARCH in self.detect.clean_mode:
            mean = Comparer._compare_hill_climb(replay1, replay2, self.detect.clean_mode.search_step)
        else:
            result = Comparer._compare_two_replays(replay1, replay2)
            mean = result[0]
            sigma = result[1]
        
        ischeat = False
        if(mean < self.detect.steal_thresh):
            ischeat = True

        return ReplayStealingResult(replay1, replay2, mean, ischeat)

    @staticmethod
    def _compare_hill_climb(replay1, replay2, dt):
        previous1 = replay1
        prev_value = 100  # whatever high value

        mode = CleanMode(CleanMode.ALIGN + CleanMode.SYNCHRONIZE)

        for _ in range(10):
            values = {}
            
            for sgn in [-1, 1]:
                attempt1 = ReplayModified.copy(previous1).shift(0, 0, sgn * dt)

                t1, t2 = ReplayModified.clean_set([attempt1, replay2], mode)
                
                value = Comparer._compare_two_replays(t1, t2)[0]

                values[value] = attempt1

            min_value = min(values)

            if min_value < prev_value:
                prev_value = min_value
                previous1 = values[min_value]
            else:
                break

        return prev_value

    @staticmethod
    def _compare_two_replays(replay1, replay2):
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
        tuple[float, float]
            (average distance, stddev) of the cursors of the two replays.
        """

        # get all coordinates in numpy arrays so that they're arranged like:
        # [ x_1 x_2 ... x_n
        #   y_1 y_2 ... y_n ]
        # indexed by columns first.
        data1 = replay1.as_list_with_timestamps()
        data2 = replay2.as_list_with_timestamps()

        # interpolate
        (data1, data2) = utils.interpolate(data1, data2)

        # remove time and keys from each tuple
        data1 = [d[1:3] for d in data1]
        data2 = [d[1:3] for d in data2]
        
        if (Mod.HR in replay1.mods) ^ (Mod.HR in replay2.mods): # xor, if one has hr but not the other
            for d in data1:
                d[1] = 384 - d[1]

        (mu, sigma) = Comparer._compute_data_similarity(data1, data2)
        return (mu, sigma)

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
            The first set of cursor data, containing the x and y positions
            of the cursor at each datapoint.

        Returns
        -------
        tuple[float, float]
            (average distance, stddev) between the two datasets.

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

        mu, sigma = distance.mean(), distance.std()

        return (mu, sigma)

    def __repr__(self):
        return f"Comparer(threshold={self.detect.steal_thresh},replays1={self.replays1},replays2={self.replays2})"

    def __str__(self):
        return f"Comparer with thresh {self.detect.steal_thresh}"
