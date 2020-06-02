import math

import numpy as np

from circleguard.enums import Key, Detect
from circleguard.result import RelaxResult, CorrectionResult, TimewarpResult

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

    def __init__(self, replay, detect, max_angle, min_distance, beatmap=None):
        self.replay = replay
        self.detect = detect
        self.max_angle = max_angle
        self.min_distance = min_distance
        self.beatmap = beatmap
        self.detect = detect

    def investigate(self):
        # equivalent of filtering out replays with no replay data from comparer on init
        if self.replay.replay_data is None:
            return
        if self.detect & Detect.RELAX:
            ur = self.ur(self.replay, self.beatmap)
            yield RelaxResult(self.replay, ur)
        if self.detect & Detect.CORRECTION:
            snaps = self.aim_correction(self.replay, self.max_angle, self.min_distance)
            yield CorrectionResult(self.replay, snaps)
        if self.detect & Detect.TIMEWARP:
            frametime = self.median_frametime(self.replay)
            yield TimewarpResult(self.replay, frametime)

    @staticmethod
    def ur(replay, beatmap):
        """
        Calculates the ur of ``replay`` when played against ``beatmap``.

        Parameters
        ----------
        replay: :class:`~.Replay`
            The replay to calculate the ur of.
        beatmap: :class:`slider.beatmap.Beatmap`
            The beatmap to calculate ``replay``'s ur with.
        """

        hitobjs = Investigator._parse_beatmap(beatmap)
        keypress_times = Investigator._parse_keypress_times(replay)
        filtered_array = Investigator._filter_hits(hitobjs, keypress_times, beatmap.overall_difficulty)
        diff_array = []

        for hitobj_time, press_time in filtered_array:
            diff_array.append(press_time - hitobj_time)
        return np.std(diff_array) * 10

    @staticmethod
    def aim_correction(replay, max_angle, min_distance):
        """
        Calculates the angle between each set of three points (a,b,c) and finds
        points where this angle is extremely acute and neither ``|ab|`` or
        ``|bc|`` are small.

        Parameters
        ----------
        replay: :class:`~.Replay`
            The replay to investigate for aim correction.
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
        # when we leave mutliple frames with the same time values, they
        # sometimes get detected (falesly) as aim correction.
        # TODO Worth looking into a bit more to see if we can avoid it without
        # removing the frames entirely.
        t, xy = Investigator.remove_unique(replay.t, replay.xy)
        t = t[1:-1]

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
        # cos(beta) = -(AC^2 - AB^2 - BC^2) / (2 * AB * BC)
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
        angle_mask = np.less(beta, max_angle, where=~np.isnan(beta))
        # boolean array of datapoints where both distance and angle requirements are met
        mask = dist_mask & angle_mask

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
    def median_frametime(replay):
        """
        Calculates the median time between the frames of ``replay``.

        Parameters
        ----------
        replay: :class:`~.Replay`
            The replay to find the median frametime of.

        Notes
        -----
        Median is used instead of mean to lessen the effect of outliers.
        """
        # replay.t is cumsum so convert it back to "time since previous frame"
        t = np.diff(replay.t)
        return np.median(t)

    @staticmethod
    def _parse_beatmap(beatmap):
        hitobjs = []

        # parse hitobj
        for hit in beatmap.hit_objects_no_spinners:
            p = hit.position
            hitobjs.append([hit.time.total_seconds() * 1000, p.x, p.y])
        return hitobjs

    @staticmethod
    def _parse_keypress_times(replay):
        keypresses = replay.k & Investigator.MASK
        changes = keypresses & ~np.insert(keypresses[:-1], 0, 0)
        return replay.t[changes != 0]

    @staticmethod
    def _filter_hits(hitobjs, keypress_times, OD):
        array = []
        hitwindow = 150 + 50 * (5 - OD) / 5

        object_i = 0
        press_i = 0

        while object_i < len(hitobjs) and press_i < len(keypress_times):
            hitobj_time = hitobjs[object_i][0]
            press_time = keypress_times[press_i]

            if press_time < hitobj_time - hitwindow / 2:
                press_i += 1
            elif press_time > hitobj_time + hitwindow / 2:
                object_i += 1
            else:
                array.append([hitobj_time, press_time])
                press_i += 1
                object_i += 1

        return array

    # TODO (some) code duplication with this method and a similar one in
    # ``Comparer``. Refactor Investigator and Comparer to inherit from a base
    # class, or move this method to utils. Preferrably the former.
    @staticmethod
    def remove_unique(t, k):
        t, t_sort = np.unique(t, return_index=True)
        k = k[t_sort]
        return (t, k)

class Snap():
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

    def __eq__(self, other):
        return (self.time == other.time and self.angle == other.angle
                and self.distance == other.distance)
