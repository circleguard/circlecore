import numpy as np
from circleguard.enums import Keys
from circleguard.result import RelaxResult
import circleguard.utils as utils

class Investigator:
    """
    A class for checking isolated replays for cheats.

    See Also:
        Comparer
    """
    # casting necessary for performance reasons
    KEYS = [int(Keys.K1), int(Keys.K2)]

    def __init__(self, replay, beatmap, threshold):
        """
        Initializes an Investigator instance.

        Attributes:
            Replay replay: The Replay object to investigate.
            slider.Beatmap beatmap: The beatmap to calculate ur with.
            Integer threshold: If a replay has a lower ur than this value,
                    it is considered a cheted repaly.
        """
        self.replay = replay
        self.data = replay.as_list_with_timestamps()
        self.beatmap = beatmap
        self.threshold = threshold
        self.last_keys = [0, 0]

    def investigate(self):
        ur = self.ur()
        ischeat = True if ur < self.threshold else False
        yield RelaxResult(self.replay, ur, ischeat)

    def ur(self):
        hitobjs = self._parse_beatmap(self.beatmap)
        keypresses = self._parse_keys(self.data)
        filtered_array = self._filter_hits(hitobjs, keypresses)
        diff_array = []

        for hit, press in filtered_array:
            diff_array.append(press[0]-hit[0])
        return np.std(diff_array) * 10

    def _parse_beatmap(self, beatmap):
        hitobjs = []

        # parse hitobj
        for hit in beatmap.hit_objects_no_spinners:
            p = hit.position
            hitobjs.append([hit.time.total_seconds() * 1000, p.x, p.y])
        return hitobjs

    def _parse_keys(self, replay):
        self.last_keys = [0, 0]
        keypresses = [keypress for keypress in replay if self._check_keys(keypress[3])]
        return keypresses

    def _check_keys(self, pressed):
        checks = [pressed & key for key in self.KEYS]
        if checks != self.last_keys and any(checks):
            if not all(self.last_keys):  # skip if user was holding both buttons in previous event
                self.last_keys = checks
                return True
        self.last_keys = checks
        return False

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
