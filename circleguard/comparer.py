import itertools
import sys
import logging
import math

import numpy as np

from circleguard.loadable import Replay
from circleguard.enums import Mod
from circleguard.exceptions import InvalidArgumentsException, CircleguardException
import circleguard.utils as utils
from circleguard.result import ReplayStealingResult

class Comparer:
    """
    Manages comparing :class:`~.replay.Replay`\s for replay stealing.

    Parameters
    ----------
    threshold: int
        If a comparison scores below this value, the :class:`~.result.Result`
        of the comparison is considered cheated.
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

    def __init__(self, threshold, replays1, replays2=None):
        self.log = logging.getLogger(__name__)
        self.threshold = threshold

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
        result = Comparer._compare_two_replays(replay1, replay2)
        result2 = Comparer._compare_hill_climb(replay1, replay2)
        print(f"normal comparison: {result[0]:.6f}, hill climb: {result2:.6f}")
        mean = result[0]
        sigma = result[1]
        ischeat = False
        if(mean < self.threshold):
            ischeat = True

        return ReplayStealingResult(replay1, replay2, mean, ischeat)

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

        (mu, sigma) = Comparer._compute_data_similarity(xy1, xy2)
        return (mu, sigma)

    @staticmethod
    def _compare_hill_climb(replay1, replay2):
        """
        Shifts two :class:`~.replay.Replay`\s through time to find a local
        minimum for similarity values.

        Parameters
        ----------
        replay1: :class:`~.replay.Replay`
            The first replay to compare.
        replay2: :class:`~.replay.Replay`
            The second replay to compare.

        Returns
        -------
        float
            The similarity value after having shifted the replays through time
            to a local similarity minimum.

       Notes
        -----
        Specifically, this method uses hill climbing with a step size of
        ``search_mode.search_step`` and a step # limit of
        ``search_mode.step_limit``. An overview follows:
        * shift the time values of the first replay ``search_step``
          milliseconds to the left and the right.
        * Clean the two replays with  ``FastCMode`` and calculate the
          similarity value of the two replays for both the left and right time
          shift.
        * Take the shift (and time values) which minimized the similarity.
          Repeat the process, taking those new time values as the starting
          point.
        * If neither the shift to the left nor right produces a lower similarity
          than the previous time values, we are at a local minimum. Return the
          current similarity.
        """

        t1, xy1, k1 = replay1.t, replay1.xy, replay1.k
        t2, xy2, k2 = replay2.t, replay2.xy, replay2.k
        prev_value = math.inf # arbitrarily high value

        dt = 16
        step_limit = 10

        for _ in range(step_limit):
            values = {}

            # try shifting both backwards and forwards in time
            for sgn in [-1, 1]:
                replay1.t = t1 + sgn * dt
                v = replay1.t

                value = Comparer._compare_two_replays(replay1, replay2)[0]

                values[value] = v
                replay1.t, replay1.xy, replay1.k = t1, xy1, k1
                replay2.t, replay2.xy, replay2.k = t2, xy2, k2

            # take the times with the lowest similarity
            min_value = min(values)

            if min_value < prev_value:
                prev_value = min_value
                t1 = values[min_value]
            # if the lowest value isn't better than our current, we're at
            # a local min. Break and return our current similarity value.
            else:
                break

        return prev_value


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
        return f"Comparer(threshold={self.threshold},replays1={self.replays1},replays2={self.replays2})"

    def __str__(self):
        return f"Comparer with thresh {self.threshold}"
