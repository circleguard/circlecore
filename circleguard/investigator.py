from osu_parser.osu_parser.beatmap import Beatmap
import numpy as np

class Investigator:
    """
    A class for checking isolated replays for cheats.

    See Also:
        Comparer
    """
    def __init__(self, replay, beatmap_path):
        self.replay = replay.as_list_with_timestamps()
        self.beatmap = Beatmap(beatmap_path)

    def ur(self):
        hitobjs = self._parse_beatmap(self.beatmap)
        keypresses = self._parse_keys(self.replay)
        hitwindow = 150 + 50 * (5 - self.beatmap.difficulty["OverallDifficulty"]) / 5
        diff_array = []

        # inefficient as fugg, but not important rn
        # filters out all clicks that didn't hit anything and stores diffs to array
        for hitobj in hitobjs:
            temp_diffs = []
            temp_times = []
            for press in keypresses:
                if hitobj > press-(hitwindow/2) and hitobj < press+(hitwindow/2):
                    temp_times.append(hitobj)
                    diff = press-hitobj
                    diff = diff if diff > 0 else diff
                    temp_diffs.append(diff)
            # only add one click per hitobj
            if len(temp_diffs) != 0:
                index = temp_diffs.index(min(temp_diffs, key=abs))
                diff_array.append(temp_diffs[index])

        return np.std(diff_array) * 10

    def _parse_beatmap(self, beatmap):
        hitobjs = []

        # parse hitobj
        for hit in beatmap.hitobjects:
            if not 8 & hit.type:
                hitobjs.append(hit.time)
        return hitobjs


    def _parse_keys(self, replay):
        keypresses = []
        flip = False
        for keypress in replay:
            if keypress[3] == 5 or keypress[3] == 10:
                if not flip:
                    flip = True
                    keypresses.append(keypress[0])
            else:
                if flip:
                    flip = False
        return keypresses
