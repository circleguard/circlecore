
import numpy as np
from circleguard.enums import Key, Detect
from circleguard.result import RelaxResult, CorrectionResult, MacroResult
import circleguard.utils as utils
import math

class Investigator:
    """
    Manages the investigation of individual
    :class:`~.replay.Replay`\s for cheats.

    Parameters
    ----------
    replay: :class:`~.replay.Replay`
        The replay to investigate.
    detect: :class:`~.Detect`
        What cheats to investigate the replay for.
    beatmap: :class:`slider.beatmap.Beatmap`
        The beatmap to calculate ur from, with the replay. Should be ``None``
        if ``Detect.RELAX in detect`` is ``False``.

    See Also
    --------
    :class:`~.comparer.Comparer`, for comparing multiple replays.
    """

    MASK = int(Key.M1) | int(Key.M2)

    def __init__(self, replay, detect, beatmap=None):

        self.replay = replay
        # TODO np.array is called on replay.as_list_with_timestamps with object=dtype,
        # and we'll probably want a np array for speed in aim_correction as well.
        # If that object param isn't necessary we can call np.array in init
        self.replay_data = replay.as_list_with_timestamps()
        self.detect = detect
        self.beatmap = beatmap
        self.detect = detect

    def investigate(self):
        d = self.detect
        # TODO we're iterating over the replay three separate times here if
        # all three detects are passed; certainly not the most efficient way
        # to do it. Figure out how to keep the code clean but do all three tests
        # in a single O(n) pass through the replay (or whatever the best case
        # happens to be).
        if Detect.RELAX in d:
            ur = self.ur(self.replay_data, self.beatmap)
            ischeat = ur < d.relax_max_ur
            yield RelaxResult(self.replay, ur, ischeat)
        if Detect.CORRECTION in d:
            snaps = self.aim_correction(self.replay_data, d.correction_max_angle, d.correction_min_distance)
            ischeat = len(snaps) > 1
            yield CorrectionResult(self.replay, snaps, ischeat)
        if Detect.MACRO in d:
            presses = self.macro_detection(self.replay_data, self.beatmap, d.macro_max_length)
            ischeat = len(presses) > d.macro_min_count
            yield MacroResult(self.replay, presses, ischeat)

    @staticmethod
    def ur(replay_data, beatmap):
        """
        Calculates the ur of ``replay_data`` when played against ``beatmap``.
        """

        hitobjs = Investigator._parse_beatmap(beatmap)
        keypresses = Investigator._parse_keys(replay_data)
        filtered_array = Investigator._filter_hits(hitobjs, keypresses, beatmap.overall_difficulty)
        diff_array = []

        for hit, press, _ in filtered_array:
            diff_array.append(press[0]-hit[0])
        return np.std(diff_array) * 10

    @staticmethod
    def aim_correction(replay_data, max_angle, min_distance):
        """
        Calculates the angle between each set of three points (a,b,c) and finds
        points where this angle is extremely acute neither ``|ab|`` or
        ``|bc|`` are
        small.

        Parameters
        ----------
        replay_data: list[int, float, float, int]
            A list of replay datapoints; [[time, x, y, keys_pressed], ...].
        max_angle: float
            Consider only (a,b,c) where ``∠abc < max_angle``
        min_distance: float
            Consider only (a,b,c) where ``|ab| > min_distance`` and
            ``|ab| > min_distance``.

        Returns
        -------
        list[:class:`~.Snap`]
            Hits where the angle was less than ``max_angle`` and the distance
            was more than ``min_distance``.

        Notes
        -----
        This does not detect correction where multiple datapoints are placed
        at the correction site (which creates a small ``min_distance``).

        Another possible method is to look at the ratio between the angle
        and distance.

        See Also
        --------
        :meth:`~.aim_correction_sam` for an alternative, unused approach
        involving velocity and jerk.
        """
        data = np.array(replay_data).T

        t, xy = data[0][1:-1], data[1:3].T

        # labelling three consecutive points a, b and c
        ab = xy[1:-1] - xy[:-2]
        bc = xy[2:] - xy[1:-1]
        ac = xy[2:] - xy[:-2]
        # Distance a to b, b to c, and a to c
        AB = np.linalg.norm(ab, axis=1)
        BC = np.linalg.norm(bc, axis=1)
        AC = np.linalg.norm(ac, axis=1)
        # Law of cosines, solve for beta
        # AC^2 = AB^2 + BC^2 - 2 * AB * BC * cos(beta)
        # cos(beta) = -(AC^2 - AB^2 - BC^2) / (2*AB*BC)
        num = -(AC ** 2 - AB ** 2 - BC ** 2)
        denom = (2 * AB * BC)
        # use true_divide for handling division by zero
        cos_beta = np.true_divide(num, denom, out=np.full_like(num, np.nan), where=denom!=0)
        # rounding issues makes cos_beta go out of arccos' domain, so restrict it
        cos_beta = np.clip(cos_beta, -1, 1)

        beta = np.rad2deg(np.arccos(cos_beta))

        min_AB_BC = np.minimum(AB, BC)
        dist_mask = min_AB_BC > min_distance
        # use less to avoid comparing to nan
        angl_mask = np.less(beta, max_angle, where=~np.isnan(beta))
        # boolean array of datapoints where both distance and angle requirements are met
        mask = dist_mask & angl_mask

        return [Snap(t, b, d) for (t, b, d) in zip(t[mask], beta[mask], min_AB_BC[mask])]

    @staticmethod
    def aim_correction_sam(replay_data, num_jerks, min_jerk):
        """
        Calculates the jerk at each moment in the Replay, counts the number of times
        it exceeds min_jerk and reports a positive if that number is over num_jerks.
        Also reports all suspicious jerks and their timestamps.

        WARNING
        -------
        Unused function. Kept for historical purposes and ease of viewing in
        case we want to switch to this track of aim correction in the future,
        or provide it as an alternative.
        """

        # get all replay data as an array of type [(t, x, y, k)]
        txyk = np.array(replay_data)

        # drop keypresses
        txy = txyk[:, :3]

        # separate time and space
        t = txy[:, 0]
        xy = txy[:, 1:]

        # j_x = (d/dt)^3 x
        # calculated as (d/dT dT/dt)^3 x = (dT/dt)^3 (d/dT)^3 x
        # (d/dT)^3 x = d(d(dx/dT)/dT)/dT
        # (dT/dt)^3 = 1/(dt/dT)^3
        dtdT = np.diff(t)
        d3xy = np.diff(xy, axis=0, n=3)
        # safely calculate the division and replace with zero if the divisor is zero
        # dtdT is sliced with 2: because differentiating drops one element for each order (slice (n - 1,) to (n - 3,))
        # d3xy is of shape (n - 3, 2) so dtdT is also reshaped from (n - 3,) to (n - 3, 1) to align the axes.
        jerk = np.divide(d3xy, dtdT[2:, None] ** 3, out=np.zeros_like(d3xy), where=dtdT[2:,None]!=0)

        # take the absolute value of the jerk
        jerk = np.linalg.norm(jerk, axis=1)

        # create a mask of where the jerk reaches suspicious values
        anomalous = jerk > min_jerk
        # and retrieve and store the timestamps and the values themself
        timestamps = t[3:][anomalous]
        values = jerk[anomalous]
        # reshape to an array of type [(t, j)]
        jerks = np.vstack((timestamps, values)).T

        # count the anomalies
        ischeat = anomalous.sum() > num_jerks

        return [jerks, ischeat]

    @staticmethod
    def macro_detection(replay_data, beatmap, max_length):
        """
        Returns a list of :meth:`~.Press`\s that have a longer press_length than ``max_length``.

        Parameters
        ----------
        replay_data: list[int, float, float, int]
            A list of replay datapoints; [[time, x, y, keys_pressed], ...].
        beatmap: :class:`slider.beatmap.Beatmap`
            The beatmap to which the Presses are mapped to.

        Returns
        -------
        list[:class:`~.Press`]
            A list of :meth:`~.Press`\s
        """
        hm = Investigator.hit_map(replay_data, beatmap)
        presses = [press for press in hm if press.press_length < max_length]
        return presses

    @staticmethod
    def _parse_beatmap(beatmap):
        """
        Parses the beatmap.

        Parameters
        ----------
        beatmap: :class:`slider.beatmap.Beatmap`
            The beatmap from which to extract the hit objects from.

        Returns
        -------
        list
            A list of beatmap hitobjects; [[time, x, y], ...].
        """
        hitobjs = []

        # parse hitobj
        for hit in beatmap.hit_objects_no_spinners:
            p = hit.position
            hitobjs.append([hit.time.total_seconds() * 1000, p.x, p.y])
        return hitobjs

    @staticmethod
    def _parse_keys(data):
        """
        Parses the raw replay data into presses and releases.

        Parameters
        ----------
        data: list[int, float, float, int]
            A list of replay datapoints; [[time, x, y, keys_pressed], ...].

        Returns
        -------
        list
            A list of keypress events, each consisting of two arrays;
            [[[time, x, y, keys_pressed],[time, x, y, keys_pressed]] ...]
            The first array represents the start of a press, the second one represents the end of the press.
        """
        data = np.array(data, dtype=object)
        presses = []
        buffer_k1 = None
        buffer_k2 = None
        for i in data:
            if Key.M1 in Key(i[3]) and buffer_k1 is None:
                d = i
                d[3] = int(Key(d[3]) & Key.K1 | Key(d[3]) & Key.M1)
                buffer_k1 = d
            elif Key.M1 not in Key(i[3]) and buffer_k1 is not None:
                presses.append([buffer_k1, i])
                buffer_k1 = None

            if Key.M2 in Key(i[3]) and buffer_k2 is None:
                d = i
                d[3] = int(Key(d[3]) & Key.K2 | Key(d[3]) & Key.M2)
                buffer_k2 = d
            elif Key.M2 not in Key(i[3]) and buffer_k2 is not None:
                presses.append([buffer_k2, i])
                buffer_k2 = None
        return np.array(presses)

    @staticmethod
    def hit_map(replay_data, beatmap):
        """
        Generates a list of :meth:`~.Press`\s.

        Parameters
        ----------
        replay_data: list[int, float, float, int]
            A list of replay datapoints; [[time, x, y, keys_pressed], ...].
        beatmap: :class:`slider.beatmap.Beatmap`
            The beatmap to which the Presses are mapped to.

        Returns
        -------
        list[:class:`~.Press`]
            A list of :meth:`~.Press`\s

        """
        hitobjs = Investigator._parse_beatmap(beatmap)
        keypresses = Investigator._parse_keys(replay_data)
        filtered_array = Investigator._filter_hits(hitobjs, keypresses, beatmap.overall_difficulty)
        array = []
        for hit, press_begin, press_end in filtered_array:
            array.append(Press(hit, press_begin, press_end))
        return array

    @staticmethod
    def _filter_hits(hitobjs, keypresses, OD):
        """
        Maps ``hitobjs`` onto ``keypresses``, removing all useless ``keypresses`` in the process.
        This class is expected to be used with the output of :meth:`~._parse_beatmap()` and :meth:`~._parse_keys`

        Parameters
        ----------
        hitobjs: list
            A list of beatmap hitobjects; [[time, x, y], ...]. Usually the direct output of :meth:`~._parse_beatmap()`
        keypresses: list
            A list of keypress events, each consisting of two arrays;
            [[[time, x, y, keys_pressed],[time, x, y, keys_pressed]] ...]
            The first array represents the start of a press, the second one represents the end of the press.
            Usually the direct output of :meth:`~._parse_keys`
        OD: float
            The Overall Difficulty to calculate the hitwindow from.

        Returns
        -------
        list
            A list of hit events; ``[[hitobj, press[0], press[1]], ...]``.
        """
        array = []
        hitwindow = 150 + 50 * (5 - OD) / 5

        object_i = 0
        press_i = 0

        while object_i < len(hitobjs) and press_i < len(keypresses):
            hitobj = hitobjs[object_i]
            press = keypresses[press_i]

            if press[0][0] < hitobj[0] - hitwindow / 2:
                press_i += 1
            elif press[0][0] > hitobj[0] + hitwindow / 2:
                object_i += 1
            else:
                array.append([hitobj, press[0], press[1]])
                press_i += 1
                object_i += 1

        return array


class Snap:
    """
    A suspicious hit in a replay, specifically so because it snaps away from
    the otherwise normal path. Snaps currently represent the middle datapoint
    in a set of three replay datapoints.

    Parameters
    ----------
    time: int
        The time value of the middle datapoint, in ms. 0 represents the
        beginning of the replay.
    angle: float
        The angle between the three datapoints.
    distance: float
        ``min(dist_a_b, dist_b_c)`` if ``a``, ``b``, and ``c`` are three
        datapoints with ``b`` being the middle one.

    See Also
    --------
    :meth:`~.Investigator.aim_correction`
    """
    def __init__(self, time, angle, distance):
        self.time = time
        self.angle = angle
        self.distance = distance

class Press:
    """
    Represents a hit in a replay. This class is expected to be used with the output of :meth:`~._filter_hits()`

    Parameters
    ----------
    hitobj: list[int, float, float]
        A list consisting of the hit object time, x and y; [t, x, y]
    hit_begin: list[int, float, float, int]
        A replay datapoint; [time, x, y, keys_pressed]. This is the beginning of the Press.
    hit_end: list[int, float, float, int]
        A replay datapoint; [time, x, y, keys_pressed]. This is the end of the Press.

    Attributes
    ----------
    x : float
        The Δ of the X coordinate from hitobj and hit_begin
    y : float
        The Δ of the Y coordinate from hitobj and hit_begin
    error: int
        The Δ of the time from hitobj and hit_begin
    press_length: int
        Amount of time between hit_begin and hit_end
    key: int
        The Key which was used to press. Calculated by subtracting hit_end from the hit_begin


    See Also
    --------
    :meth:`~.Investigator.hit_map`
    """
    def __init__(self, hitobj, hit_begin, hit_end):
        self.x = hit_begin[1]-hitobj[1]
        self.y = hit_begin[2]-hitobj[2]
        self.error = hit_begin[0]-hitobj[0]
        self.press_length = hit_end[0] - hit_begin[0]
        self.key = Key(hit_begin[3] - hit_end[3])
