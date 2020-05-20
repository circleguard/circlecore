import itertools
import sys
import logging
import math

import numpy as np
from scipy import signal, stats

from circleguard.loadable import Replay
from circleguard.enums import Detect
from circleguard.mod import Mod
from circleguard.exceptions import InvalidArgumentsException, CircleguardException
import circleguard.utils as utils
from circleguard.result import StealResultSim, StealResultCorr

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

    def __init__(self, replays1, replays2, detect):
        self.log = logging.getLogger(__name__)

        # filter beatmaps we had no data for
        self.replays1 = [replay for replay in replays1 if replay.replay_data is not None]
        self.replays2 = [replay for replay in replays2 if replay.replay_data is not None] if replays2 else None

        self.mode = "double" if self.replays2 else "single"
        self.detect = detect

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

        # can't make any comparisons
        if not self.replays1:
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
            yield from self.compare_two_replays(replay1, replay2)


    def compare_two_replays(self, replay1, replay2):
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

        # perform preprocessing here as an optimization, so it is not repeated
        # within different comparison algorithms. This will likely need to
        # become more advanced if we add more (and different) algorithms.

        # interpolation breaks when multiple frames have the same time values
        # (which occurs semi frequently in replays). So filter them out
        t1, xy1 = Comparer.remove_unique(replay1.t, replay1.xy)
        t2, xy2 = Comparer.remove_unique(replay2.t, replay2.xy)
        xy1, xy2 = Comparer.interpolate(t1, t2, xy1, xy2)
        xy1, xy2 = Comparer.clean(xy1, xy2)

        # flip if one but not both has HR
        if (Mod.HR in replay1.mods) ^ (Mod.HR in replay2.mods):
            xy1[:, 1] = 384 - xy1[:, 1]

        if Detect.STEAL_SIM & self.detect:
            mean = Comparer.compute_similarity(xy1, xy2)
            yield StealResultSim(replay1, replay2, mean)
        if Detect.STEAL_CORR & self.detect:
            correlation = Comparer.compute_correlation(xy1, xy2)
            yield StealResultCorr(replay1, replay2, correlation)


    @staticmethod
    def compute_similarity(xy1, xy2):
        """
        Calculates the average distance between two sets of cursor position
        data.

        Parameters
        ----------
        replay1: ndarray
            The first xy data to compare.
        replay2: ndarray
            The second xy data to compare.

        Returns
        -------
        float
            The mean distance between the two datasets.
        """

        # euclidean distance
        distance = xy1 - xy2
        distance = (distance ** 2).sum(axis=1) ** 0.5
        return distance.mean()

    @staticmethod
    def compute_correlation(xy1, xy2, num_chunks=1):

        xy1 = xy1.T
        xy2 = xy2.T

        # section into chunks, used to reduce the effect of outlier data
        # (eg. cheater inserts replay data during breaks that places them
        # far away from the actual replay)
        horizontal_length = xy1.shape[1] - xy1.shape[1] % num_chunks
        xy1_parts = np.hsplit(xy1[:,:horizontal_length], num_chunks)
        xy2_parts = np.hsplit(xy2[:,:horizontal_length], num_chunks)
        correlations = []
        for (xy1_part, xy2_part) in zip(xy1_parts, xy2_parts):
            xy1_part -= np.mean(xy1_part)
            xy2_part -= np.mean(xy2_part)
            norm = np.std(xy1_part) * np.std(xy2_part) * xy1_part.size
            # matrix of correlations between xy1 and xy2 at different time
            # shifts
            cross_corr_matrix = signal.correlate(xy1_part, xy2_part) / norm

            # pick the maximum correlation, which will probably be at 0
            # time shift, unless the replays have been intentionally shifted in
            # time
            max_corr = np.max(cross_corr_matrix)
            correlations.append(max_corr)
        # take the median of all the chunks to reduce the effect of outliers
        return np.median(correlations)


    @staticmethod
    def remove_unique(t, xy):
        t, t_sort = np.unique(t, return_index=True)
        xy = xy[t_sort]
        return (t, xy)


    @staticmethod
    def interpolate(t1, t2, xy1, xy2):
        """
        Interpolates the xy data of the shorter replay to the longer replay.

        Returns
        -------
        (ndarray, ndarray)
            The interpolated replay data of the first and second replay
            respectively.

        Notes
        -----
        The length of the two returned arrays will be equal. This is a (desired)
        side effect of interpolating.
        """

        if len(t1) > len(t2):
            xy2x = np.interp(t1, t2, xy2[:, 0])
            xy2y = np.interp(t1, t2, xy2[:, 1])
            xy2 = np.array([xy2x, xy2y]).T
        else:
            xy1x = np.interp(t2, t1, xy1[:, 0])
            xy1y = np.interp(t2, t1, xy1[:, 1])
            xy1 = np.array([xy1x, xy1y]).T

        return (xy1, xy2)


    @staticmethod
    def clean(xy1, xy2):
        """
        Cleans the given xy data to only include indices where both coordinates
        are inside the osu gameplay window (a 512 by 384 osu!pixel window).

        Warnings
        --------
        The length of the two passed arrays must be equal.
        """

        valid = np.all(([0, 0] <= xy1) & (xy1 <= [512, 384]), axis=1) & np.all(([0, 0] <= xy2) & (xy2 <= [512, 384]), axis=1)
        xy1 = xy1[valid]
        xy2 = xy2[valid]
        return (xy1, xy2)


    def __repr__(self):
        return f"Comparer(replays1={self.replays1},replays2={self.replays2})"

    def __str__(self):
        return f"Comparer with {len(self.replays1)} and {len(self.replays2)} replays"
