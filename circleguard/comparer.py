import itertools
import sys
import logging
import math

import numpy as np
import itertools as itr

from circleguard.replay import Replay
from circleguard.enums import Mod
from circleguard.exceptions import InvalidArgumentsException, CircleguardException
import circleguard.utils as utils
from circleguard.result import ReplayStealingResult

class ModifiedReplay(Replay):
    def __init__(self, timestamp, map_id, username, user_id, mods, replay_id, replay_data, weight):
        Replay.__init__(self, timestamp, map_id, username, user_id, mods, replay_id, replay_data, weight)
        self.txyk = None
    
    def load(self, loader):
        pass

    def interpolate_to(self, timestamps):
        prev_err = np.seterr(all="ignore")
        
        txyks = []

        self.as_list_with_timestamps()

        i = 1
        t_end = self.txyk[-1][0]
        
        for t in timestamps:
            if t > t_end:
                break
            
            while self.txyk[i][0] < t:
                i += 1

            r = (t - self.txyk[i - 1][0]) / (self.txyk[i][0] - self.txyk[i - 1][0])

            if np.isnan(r) or np.isinf(r):
                continue

            x = r * self.txyk[i][1] + (1 - r) * self.txyk[i - 1][1]
            y = r * self.txyk[i][2] + (1 - r) * self.txyk[i - 1][2]
            k = self.txyk[i - 1]

            txyks += [[t, x, y, k]]

        replay = ModifiedReplay.copy(self)
        replay.txyk = txyks

        np.seterr(**prev_err)

        return replay

    def shift(self, dx, dy, dt):
        txyks = []

        self.as_list_with_timestamps()

        for t, x, y, k in self.txyk:
            txyks += [[t + dt, x + dx, y + dy, k]]

        replay = ModifiedReplay.copy(self)
        replay.txyk = txyks

        return replay

    def as_list_with_timestamps(self):
        if not self.txyk:
            timestamps = np.array([e.time_since_previous_action for e in self.replay_data])
            timestamps = timestamps.cumsum()

            # zip timestamps back to data and convert t, x, y, keys to tuples
            txyk = [[z[0], z[1].x, z[1].y, z[1].keys_pressed] for z in zip(timestamps, self.replay_data)]
            # sort to ensure time goes forward as you move through the data
            # in case someone decides to make time go backwards anyway
            txyk.sort(key=lambda p: p[0])
            self.txyk = txyk
            
            return txyk
        else:
            return self.txyk
    
    #filtering
    @staticmethod
    def copy(replay):
        r = ModifiedReplay(replay.timestamp, replay.map_id, replay.username,
                      replay.user_id, replay.mods, replay.replay_id, replay.replay_data, replay.weight)
        r.txyk = replay.as_list_with_timestamps()
        return r

    @staticmethod
    def filter_single(replay):
        data = replay.as_list_with_timestamps()

        def is_valid(d):
            return 0 <= d[1] <= 512 and 0 <= d[2] <= 384

        txyk = [d1 for (d0, d1) in zip(data, data[1:]) if is_valid(d0) and is_valid(d1)]

        r = ModifiedReplay.copy(replay)
        r.loaded = True
        r.txyk = txyk

        return r

    @staticmethod
    def align_clocks(clocks):
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
                    return output

            output += [last]

    @staticmethod
    def align_coordinates(replays):
        rs = []
        
        for replay in replays:
            replay.as_list_with_timestamps()

            xs = []
            ys = []

            for _, x, y, _ in replay.txyk:
                xs += [x]
                ys += [y]

            rs += [(np.mean(xs), np.mean(ys))]

        replays = replays[:1] + [replay.shift(rs[0][0] - r[0], rs[0][1] - r[1], 0) for (replay, r)
                                in zip(replays[1:], rs[1:])]

        return replays

    @staticmethod
    def clean_set(replays, filter_valid=False, align_t=False, align_xy=False, search=None):
        replays = [ModifiedReplay.copy(r) for r in replays]

        if filter_valid:
            replays = [ModifiedReplay.filter_single(replay) for replay in replays]

        if align_t:
            timestamps = [[txyk[0] for txyk in replay.as_list_with_timestamps()] for replay in replays]

            timestamps = ModifiedReplay.align_clocks(timestamps)

            replays = [replay.interpolate_to(timestamps) for replay in replays]

        if align_xy:
            replays = ModifiedReplay.align_coordinates(replays)
        
        return replays

class Comparer:
    """
    Manages comparing :class:`~.replay.Replay`\s for replay stealing.

    Parameters
    ----------
    threshold: int
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

    def __init__(self, threshold, replays1, replays2=None, dr=1.0, dt=16):
        self.log = logging.getLogger(__name__)
        self.threshold = threshold

        # filter beatmaps we had no data for - see Loader.replay_data and OnlineReplay.from_map
        self.replays1 = [replay for replay in replays1 if replay.replay_data is not None]
        self.replays2 = [replay for replay in replays2 if replay.replay_data is not None] if replays2 else None
        self.mode = "double" if self.replays2 else "single"
        self.clean_mode = {}
        self.log.debug("Comparer initialized: %r", self)
        self.dr = dr
        self.dt = dt

    def set_clean_mode(self, options):
        self.clean_mode = options

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

        if self.mode == "single":
            self.replays1 = ModifiedReplay.clean_set(self.replays1, **self.clean_mode)

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

        if "search" in self.clean_mode and self.clean_mode["search"]:
            result = [Comparer._compare_hill_climb(replay1, replay2, self.dr, self.dt), 0]
        else:
            result = Comparer._compare_two_replays(replay1, replay2)
        
        mean = result[0]
        sigma = result[1]
        ischeat = False
        if(mean < self.threshold):
            ischeat = True

        return ReplayStealingResult(replay1, replay2, mean, ischeat)

    @staticmethod
    def _compare_hill_climb(replay1, replay2, dr, dt):
        r1copy = replay1
        v0 = Comparer._compare_two_replays(r1copy, replay2)[0]

        for _ in range(10):
            vs = {}
            
            for sgn in [-1, 1]:
                r1 = r1copy.shift(0, 0, sgn * dt)

                t1, t2 = ModifiedReplay.clean_set([r1, replay2], align_xy=True, align_t=True)
                
                v = Comparer._compare_two_replays(t1, t2)[0]

                vs[v] = r1

            vmin = min(vs)

            if vmin < v0:
                v0 = vmin
                r1copy = vs[vmin]
            else:
                break

        return v0

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
        return f"Comparer(threshold={self.threshold},replays1={self.replays1},replays2={self.replays2})"

    def __str__(self):
        return f"Comparer with thresh {self.threshold}"
