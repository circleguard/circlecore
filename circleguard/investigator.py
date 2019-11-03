
import numpy as np
from circleguard.enums import Keys, Detect
from circleguard.result import RelaxResult, CorrectionResult
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

    MASK = int(Keys.K1) | int(Keys.K2)

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
        if Detect.RELAX in d:
            ur = self.ur(self.replay_data, self.beatmap)
            ischeat = True if ur < d.max_ur else False
            yield RelaxResult(self.replay, ur, ischeat)
        if Detect.CORRECTION in d:
            suspicious_angles = self.aim_correction(self.replay_data, d.max_angle, d.min_distance)
            ischeat = len(suspicious_angles) > 1
            yield CorrectionResult(self.replay, suspicious_angles, ischeat)

    @staticmethod
    def ur(replay_data, beatmap):
        """
        Calculates the ur of ``replay_data`` when played against ``beatmap``.
        """

        hitobjs = Investigator._parse_beatmap(beatmap)
        keypresses = Investigator._parse_keys(replay_data)
        filtered_array = Investigator._filter_hits(hitobjs, keypresses, beatmap.overall_difficulty)
        diff_array = []

        for hit, press in filtered_array:
            diff_array.append(press[0]-hit[0])
        return np.std(diff_array) * 10

    @staticmethod
    def aim_correction(replay_data, max_angle, min_distance):
        """
        Calculates the angle between each set of three points and finds points
        where this angle is extremely acute (indicative of a quick jump to
        a point, then a jump back to the normal path. ie lazy aim correction by
        dragging a single point to hit the circle in the cheat editor)

        Notes
        -----
        max_angle and max_distance being passed goes a bit against the style
        here of not passing anything more than a replay/beatmap to the
        investigation functions (see: ur()), but if we don't we would iterate
        twice over this massive list of angles between every two data points.
        May be premature optimization but it just doesn't make sense to return
        a huge list and filter it in investigate().

        Returns [[float, float, float], ...] of hits where the angle was less
        than max_angle and the distance between the data points was more than
        min_distance. First float is time the hit occured, second float is angle
        between the data points in degrees, third is distance between the two
        datapoins.
        """

        suspicious_angles = []
        for idx in range(len(replay_data)):
            if idx > len(replay_data) - 3:
                # avoid indexerrors
                continue
            a = replay_data[idx]
            b = replay_data[idx + 1]
            c = replay_data[idx + 2]
            t = b[0]
            ax = a[1]
            # osr y values go "higher is lower down", convert them into normal xy plane
            # im pretty sure it works either way but debugging is so much easier when
            # you can draw vectors and compare against the visualizer. Can probably
            # remove for a practically unnoticeable speedup later
            ay = 384 - a[2]
            bx = b[1]
            by = 384 - b[2]
            cx = c[1]
            cy = 384 - c[2]
            ab = [bx - ax, by - ay]
            bc = [cx - bx, cy - by]
            # use law of cosines, we want C
            # c^2 = a^2 + b^2 − 2ab cos(C)
            # x is our c vector here; the third side of the triangle. No relation
            # to the c point in self.data which is our third point.
            # a = ab vector
            # b = bc vector
            mag_x = ((ab[0] + bc[0])**2 + (ab[1] + bc[1])**2) ** (1/2)
            mag_a = (ab[0]**2 + ab[1]**2) ** (1/2)
            mag_b = (bc[0]**2 + bc[1]**2) ** (1/2)
            try:
                frac = (mag_x**2 - mag_a**2 - mag_b**2) / (-2 * mag_a * mag_b)
                frac = max(frac, -1) # rounding issues makes it go out of acos' domain
                frac = min(frac, 1)
            except ZeroDivisionError:
                # happens when mag_a or mag_b is zero
                continue
            C = math.acos(frac)
            degrees = math.degrees(C)

            distance_a_b = (((bx - ax) ** 2) + ((by - ay) ** 2)) ** (1/2)
            if degrees < max_angle and distance_a_b > min_distance:
                suspicious_angles.append([t, degrees, distance_a_b])

        return suspicious_angles

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
    def _parse_beatmap(beatmap):
        hitobjs = []

        # parse hitobj
        for hit in beatmap.hit_objects_no_spinners:
            p = hit.position
            hitobjs.append([hit.time.total_seconds() * 1000, p.x, p.y])
        return hitobjs

    @staticmethod
    def _parse_keys(data):
        data = np.array(data, dtype=object)
        keypresses = np.int32(data[:, 3]) & Investigator.MASK
        changes = keypresses & ~np.insert(keypresses[:-1], 0, 0)
        return data[changes!=0]

    @staticmethod
    def _filter_hits(hitobjs, keypresses, OD):
        array = []
        hitwindow = 150 + 50 * (5 - OD) / 5

        object_i = 0
        press_i = 0

        while object_i < len(hitobjs) and press_i < len(keypresses):
            hitobj = hitobjs[object_i]
            press = keypresses[press_i]

            if press[0] < hitobj[0] - hitwindow / 2:
                press_i += 1
            elif press[0] > hitobj[0] + hitwindow / 2:
                object_i += 1
            else:
                array.append([hitobj, press])
                press_i += 1
                object_i += 1

        return array

class Hit:
    def __init__(self, hitobj, hit):
        self.x = hit[1]-hitobj[1]
        self.y = hit[2]-hitobj[2]
        self.error = hit[0]-hitobj[0]
        self.keys = [Keys(key_val) for key_val in utils.bits(hit[3])]
