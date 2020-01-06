import itertools
import sys
import logging
import math
import copy

import numpy as np
import itertools as itr

from circleguard.loadable import Replay
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

        if self.mode == "single" and self.detect.clean_mode.value:
            Comparer.clean_set(self.replays1, self.detect.clean_mode)

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
            mean = Comparer._compare_hill_climb(replay1, replay2, self.detect.clean_mode)
        else:
            result = Comparer._compare_two_replays(replay1, replay2)
            mean = result[0]
            sigma = result[1]

        ischeat = False
        if(mean < self.detect.steal_thresh):
            ischeat = True

        return ReplayStealingResult(replay1, replay2, mean, ischeat)

    @staticmethod
    def _compare_hill_climb(replay1, replay2, search_mode):
        """
        Shifts two :class:`~.replay.Replay` s through time greedily to
        find a local minimum for similarity values.

        Parameters
        ----------
        replay1: :class:`~.replay.Replay`
            The first replay to compare.
        replay2: :class:`~.replay.Replay`
            The second replay to compare.
        search_mode: :class:`~.enums.CleanMode`
            The time interval to search on and the maximal number of steps

        Returns
        -------
        float
            The similarity value in a local minimum.
        """

        t1, xy1, k1 = replay1.t, replay1.xy, replay1.k
        t2, xy2, k2 = replay2.t, replay2.xy, replay2.k
        prev_value = 100  # whatever high value

        clean_mode = CleanMode(CleanMode.ALIGN + CleanMode.VALIDATE)

        dt = search_mode.search_step

        for _ in range(search_mode.step_limit):
            values = {}

            for sgn in [-1, 1]:
                replay1.t = t1 + sgn * dt
                v = replay1.t

                Comparer.clean_set([replay1, replay2], clean_mode)
                value = Comparer._compare_two_replays(replay1, replay2)[0]

                values[value] = v

                replay1.t, replay1.xy, replay1.k = t1, xy1, k1
                replay2.t, replay2.xy, replay2.k = t2, xy2, k2

            min_value = min(values)

            if min_value < prev_value:
                prev_value = min_value
                t1 = values[min_value]
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

        # interpolate
        if len(replay1.t) > len(replay2.t):
            xy1 = replay1.xy
            xy2x = np.interp(replay1.t, replay2.t, replay2.xy[:, 0])
            xy2y = np.interp(replay1.t, replay2.t, replay2.xy[:, 1])
            xy2 = np.array([xy2x, xy2y]).T
        else:
            xy1x = np.interp(replay2.t, replay1.t, replay1.xy[:, 0])
            xy1y = np.interp(replay2.t, replay1.t, replay1.xy[:, 1])
            xy1 = np.array([xy1x, xy1y]).T
            xy2 = replay2.xy

        # remove time and keys from each tuple

        if (Mod.HR in replay1.mods) ^ (Mod.HR in replay2.mods): # xor, if one has hr but not the other
            for d in xy1:
                d[1] = 384 - d[1]

        (mu, sigma) = Comparer._compute_data_similarity(xy1, xy2)
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

    @staticmethod
    def interpolate_to(t_from, xy, k, t_to):
        """
        Interpolate the data to the given timestamps.
        Drops excess timestamps and creates data at missing timestamps.

        Parameters
        ----------
        t_from: ndarray[int]
            The original timestamps
        xy: ndarray[[float]]
            The coordinate data
        k: ndarray[int]
            The keypress data
        t_to: ndarray[int]
            The timestamps to interpolate to

        Returns
        -------
        ndarray[int], ndarray[[float]], ndarray[int]
            The interpolated data
        """
        xy = xy.T
        xy = np.transpose([np.interp(t_to, t_from, xy[0]), np.interp(t_to, t_from, xy[1])])
        k = k[np.searchsorted(t_from, t_to)]  # may need side="right"
        return t_to, xy, k

    @staticmethod
    def filter(t, xy, k):
        """
        Filters all timestamps with invalid coordinates.

        Parameters
        ----------
        t: ndarray[int]
            The timestamps
        xy: ndarray[[float]]
            The coordinates to filter
        k: ndarray[int]
            The keypress data

        Returns
        -------
        ndarray[int], ndarray[[float]], ndarray[int]
            The data with the invalid coordinates removed.

        Notes
        -----
        Coordinates are invalid if they are not in the range (0, 512) for the x
        coordinate and (0, 384) for the y coordinate.
        """
        valid = np.all(([0, 0] <= xy) & (xy <= [512, 384]), axis=1)

        return t[valid], xy[valid], k[valid]

    @staticmethod
    def align_clocks(clocks):
        """
        Selects suitable timestamps to which all the clocks of the replays
        could be interpolated.

        The timestamps are chosen to maximize frequency while
        also guaranteeing each replay has at least one timestamp in between
        two successive timestamps in the output.

        Parameters
        ----------
        clocks: list(ndarray[int])
            The list of arrays of timestamps the interpolation timestamps
            should be selected from.

        Returns
        -------
        ndarray[int]
            The timestamps maximizing frequency and satisfying constraints.
        """
        n = len(clocks)
        indices = [0] * n

        output = []

        def move_to(i, value):
            while clocks[i][indices[i] + 1] <= value:
                indices[i] += 1

                if indices[i] + 1 == len(clocks[i]):
                    return True

            return False

        while True:
            last = 0

            for i in range(n):
                value = clocks[i][indices[i] + 1]

                if value > last:
                    last = value

            for i in range(n):
                if move_to(i, last):
                    return np.array(output)

            output += [last]

    @staticmethod
    def align_coordinates(xys):
        """
        Shifts the coordinates so that their
        means over time coincide.

        Parameters
        ----------
        xys: ndarray[[float]]
            The coordinatess to align.

        Returns
        -------
        ndarray[[float]]
            The shifted coordinatess.

        Notes
        -----
        The first coordinates in this set is left in place, and all other
        coordinates are shifted toward its mean.
        """
        m = xys[0].mean(axis=0)

        xys = xys[:1] + [xy + (m - xy.mean(axis=0)) for xy in xys[1:]]

        return xys

    @staticmethod
    def clean_set(replays, mode):
        """
        Cleans the :class:`~.Replay`s in replays using the methods specified in the mode.

        Parameters
        ----------
        replays: list(:class:`~.Replay`)
            The replays to clean.
        mode: :class:`~.CleanMode`
            The mode specifying the used methods.

        Returns
        -------
        list(:class:`~.Replay`)
            The cleaned :class:`~.Replay`s
        """

        data = [[r.t, r.xy, r.k] for r in replays]

        if CleanMode.VALIDATE in mode:
            for d in data:
                d[:] = Comparer.filter(*d)

        if CleanMode.SYNCHRONIZE in mode:
            t = Comparer.align_clocks([d[0] for d in data])

            for d in data:
                d[:] = Comparer.interpolate_to(*d, t)

        if CleanMode.ALIGN in mode:
            for i, xy in enumerate(Comparer.align_coordinates([d[1] for d in data])):
                data[i][1] = xy

        for r, d in zip(replays, data):
            r.t = d[0]
            r.xy = d[1]
            r.k = d[2]

    def __repr__(self):
        return f"Comparer(threshold={self.detect.steal_thresh},replays1={self.replays1},replays2={self.replays2})"

    def __str__(self):
        return f"Comparer with thresh {self.detect.steal_thresh}"
