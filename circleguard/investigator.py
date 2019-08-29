
import numpy as np
from circleguard.enums import Keys
from circleguard.result import RelaxResult, AimCorrectionResult
import circleguard.utils as utils

class Investigator:
    """
    A class for checking isolated replays for cheats.

    See Also:
        Comparer
    """

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
        self.data = replay.as_list_with_timestamps()
        self.beatmap = beatmap
        self.max_ur = max_ur
        self.min_jerk = min_jerk
        self.num_jerks = num_jerks
        self.last_keys = [0, 0]

    def investigate(self):
        ur = self.ur()
        ischeat = True if ur < self.max_ur else False
        yield RelaxResult(self.replay, ur, ischeat)

    def ur(self):
        hitobjs = self._parse_beatmap(self.beatmap)
        keypresses = self._parse_keys(self.data)
        filtered_array = self._filter_hits(hitobjs, keypresses)
        diff_array = []

        for hit, press in filtered_array:
            diff_array.append(press[0]-hit[0])
        return np.std(diff_array) * 10

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
        for hit in beatmap.hitobjects:
            hitobjs.append([hit.time, hit.x, hit.y])
        return hitobjs

    def _parse_keys(self, replay):
        keypresses = []
        self.last_keys = [0, 0]
        for keypress in replay:
            if self._check_keys(keypress[3]):
                    keypresses.append(keypress)
        return keypresses

    def _check_keys(self, pressed):
        checks = [pressed & key.value for key in (Keys.K1, Keys.K2)]
        if checks != self.last_keys and any(checks):
            if not all(self.last_keys):  # skip if user was holding both buttons in previous event
                self.last_keys = checks
                return True
        self.last_keys = checks
        return False

    def _filter_hits(self, hitobjs, keypresses):
        array = []
        hitwindow = 150 + 50 * (5 - self.beatmap.difficulty["OverallDifficulty"]) / 5

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
