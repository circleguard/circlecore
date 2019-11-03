
import numpy as np
from circleguard.enums import Keys, Detect
from circleguard.result import RelaxResult, AimCorrectionResult
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
    beatmap: :class:`slider.beatmap.Beatmap`
        The beatmap to calculate ur from, with the replay.
    threshold: int
        If a replay has a lower ur than ``threshold``, it is considered cheated.

    See Also
    --------
    :class:`~.comparer.Comparer`, for comparing multiple replays.
    """
    MASK = int(Keys.K1) | int(Keys.K2)

    def __init__(self, replay, beatmap, max_ur, min_jerk, num_jerks):
        """
        Initializes an Investigator instance.

        Attributes:
            Replay replay: The Replay object to investigate.
            circleparse.Beatmap beatmap: The beatmap to calculate ur with.
            Float max_ur: If a replay has a lower ur than this value,
                    it is considered a cheated replay.
            Float min_jerk: If a replay has a jerk higher than this value at a point,
                    that is considered suspicious.
            Integer num_jerks: If a replay has more suspicious jerks than this number,
                    it is considered a cheated replay.

        """
        self.replay = replay
        self.detect = replay.detect
        self.data = replay.as_list_with_timestamps()
        self.beatmap = beatmap
        self.max_ur = max_ur
        self.min_jerk = min_jerk
        self.num_jerks = num_jerks
        self.last_keys = [0, 0]

    def investigate(self):
        if self.detect & Detect.RELAX:
            ur = self.ur()
            ischeat = True if ur < self.max_ur else False
            yield RelaxResult(self.replay, ur, ischeat)
        if self.detect & Detect.AIM_CORRECTION:
            yield from self.aim_correction_angle()

    def ur(self):
        """
        Calculates the ur of the replay being investigated.


        """
        hitobjs = self._parse_beatmap(self.beatmap)
        keypresses = self._parse_keys(self.data)
        filtered_array = self._filter_hits(hitobjs, keypresses)
        diff_array = []

        for hit, press in filtered_array:
            diff_array.append(press[0]-hit[0])
        return np.std(diff_array) * 10

    def aim_correction_angle(self):
        """
        Calculates the angle between each set of three points and finds points
        where this angle is extremely acute (indicative of a quick jump to
        a point, then a jump back to the normal path. ie lazy aim correction by
        dragging a single point to hit the circle in the cheat editor)
        """

        for idx in range(len(self.data)):
            if idx > len(self.data) - 3:
                # avoid indexerrors
                continue
            a = self.data[idx]
            b = self.data[idx + 1]
            c = self.data[idx + 2]
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
            except ZeroDivisionError:
                # happens when mag_a or mag_b is zero
                continue
            C = math.acos(frac)
            degrees = math.degrees(C)

            distance_a_b = (((bx - ax) ** 2) + ((by - ay) ** 2)) ** (1/2)
            if degrees < 10 and distance_a_b > 3:
                print(t, degrees)

        yield self.replay


    def aim_correction(self):
        """
        Calculates the jerk at each moment in the Replay, counts the number of times
        it exceeds min_jerk and reports a positive if that number is over num_jerks.
        Also reports all suspicious jerks and their timestamps.
        """

        # get all replay data as an array of type [(t, x, y, k)]
        txyk = np.array(self.data)

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
        anomalous = jerk > self.min_jerk
        # and retrieve and store the timestamps and the values themself
        timestamps = t[3:][anomalous]
        values = jerk[anomalous]
        # reshape to an array of type [(t, j)]
        jerks = np.vstack((timestamps, values)).T

        # count the anomalies
        ischeat = anomalous.sum() > self.num_jerks

        yield AimCorrectionResult(self.replay, jerks, ischeat)

    def _parse_beatmap(self, beatmap):
        hitobjs = []

        # parse hitobj
        for hit in beatmap.hit_objects_no_spinners:
            p = hit.position
            hitobjs.append([hit.time.total_seconds() * 1000, p.x, p.y])
        return hitobjs

    def _parse_keys(self, data):
        data = np.array(data, dtype=object)
        keypresses = np.int32(data[:, 3]) & self.MASK
        changes = keypresses & ~np.insert(keypresses[:-1], 0, 0)
        return data[changes!=0]

    def _filter_hits(self, hitobjs, keypresses):
        array = []
        hitwindow = 150 + 50 * (5 - self.beatmap.overall_difficulty) / 5

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
