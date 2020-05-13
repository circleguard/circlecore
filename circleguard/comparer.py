import itertools
import sys
import logging
import math

import numpy as np
from scipy import signal, stats

from circleguard.loadable import Replay
from circleguard.enums import Mod, Detect
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

        if Detect.STEAL_SIM & self.detect:
            mean = Comparer.compute_similarity(replay1, replay2)
            yield StealResultSim(replay1, replay2, mean)
        if Detect.STEAL_CORR & self.detect:
            correlation = Comparer.compute_correlation(replay1, replay2)
            yield StealResultCorr(replay1, replay2, correlation)


    @staticmethod
    def compute_similarity(replay1, replay2):
        """
        Calculates the average cursor distance between two
        :class:`~.replay.Replay`\s after interpolation and filtering.

        Parameters
        ----------
        replay1: :class:`~.replay.Replay`
            The first replay to compare.
        replay2: :class:`~.replay.Replay`
            The second replay to compare.

        Returns
        -------
        float
            The mean distance of the cursors of the two replays.
        """

        # interpolate
        if len(replay1.t) > len(replay2.t):
            # implicit fast copy to avoid overwriting this array on replay1
            # when flipping for HR
            xy1 = np.array(replay1.xy)

            xy2x = np.interp(replay1.t, replay2.t, replay2.xy[:, 0])
            xy2y = np.interp(replay1.t, replay2.t, replay2.xy[:, 1])
            xy2 = np.array([xy2x, xy2y]).T
        else:
            xy1x = np.interp(replay2.t, replay1.t, replay1.xy[:, 0])
            xy1y = np.interp(replay2.t, replay1.t, replay1.xy[:, 1])
            xy1 = np.array([xy1x, xy1y]).T
            # implicit fast copy to avoid overwriting this array on replay2
            # when flipping for HR
            xy2 = np.array(replay2.xy)

        valid = np.all(([0, 0] <= xy1) & (xy1 <= [512, 384]), axis=1) & np.all(([0, 0] <= xy2) & (xy2 <= [512, 384]), axis=1)
        xy1 = xy1[valid]
        xy2 = xy2[valid]

        # flip if one but not both has HR
        if (Mod.HR in replay1.mods) ^ (Mod.HR in replay2.mods):
            xy1[:, 1] = 384 - xy1[:, 1]

        # euclidean distance
        distance = xy1 - xy2
        distance = (distance ** 2).sum(axis=1) ** 0.5
        mean = distance.mean()
        return mean

    @staticmethod
    def compute_correlation(replay1, replay2, num_chunks=1):
        # copy arrays, as we'll be modifying them
        xy1 = np.array(replay1.xy)
        xy2 = np.array(replay2.xy)

        # flip if one but not both has HR
        if (Mod.HR in replay1.mods) ^ (Mod.HR in replay2.mods):
            xy1[:, 1] = 384 - xy1[:, 1]

        xy1 = xy1.T
        xy2 = xy2.T

        # Sectioned into 20 chunks, used to ignore outliers (eg. long replay
        # with breaks is copied, and the cheater cursordances during the break)
        horizontal_length = xy1.shape[1] - xy1.shape[1] % num_chunks
        xy1_sections = np.hsplit(xy1[:,:horizontal_length], num_chunks)
        xy2_sections = np.hsplit(xy2[:,:horizontal_length], num_chunks)
        correlations = []
        for (xy1_section, xy2_section) in zip(xy1_sections, xy2_sections):
            xy1_section -= np.mean(xy1_section)
            xy2_section -= np.mean(xy2_section)
            norm = np.std(xy1_section) * np.std(xy2_section) * xy1_section.size
            cross_correlation_matrix = signal.correlate(xy1_section, xy2_section) / norm
            # Pick the lag with the maximum correlation, this likely in
            # most cases is 0 lag
            max_correlation = np.max(cross_correlation_matrix)
            correlations.append(max_correlation)
        # take the median of all the chunks so we throw away any outliers
        return np.median(correlations)

    def __repr__(self):
        return f"Comparer(replays1={self.replays1},replays2={self.replays2})"

    def __str__(self):
        return f"Comparer with {len(self.replays1)} and {len(self.replays2)} replays"
