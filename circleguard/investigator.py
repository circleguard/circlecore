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

    def __init__(self, replay, beatmap, threshold):
        """
        Initializes an Investigator instance.

        Attributes:
            Replay replay: The Replay object to investigate.
            circleparse.Beatmap beatmap: The beatmap to calculate ur with.
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
        # inefficient as fugg, but not important rn
        # filters out all clicks that didn't hit anything and stores hit and hitobj to array
        for hitobj in hitobjs:
            temp_diffs = []
            temp_hits = []
            for press in keypresses:
                if hitobj[0] > press[0]-(hitwindow/2) and hitobj[0] < press[0]+(hitwindow/2):
                    diff = press[0]-hitobj[0]
                    temp_diffs.append(diff)
                    temp_hits.append(press)
            # only add one click per hitobj
            if len(temp_diffs) != 0:
                index = temp_diffs.index(min(temp_diffs, key=abs))
                array.append([hitobj, temp_hits[index]])
                keypresses.pop(keypresses.index(temp_hits[index]))  # remove used hits
        return array

class Hit:
    def __init__(self, hitobj, hit):
        self.x = hit[1]-hitobj[1]
        self.y = hit[2]-hitobj[2]
        self.error = hit[0]-hitobj[0]
        self.keys = [Keys(key_val) for key_val in utils.bits(hit[3])]
