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
        last = 0
        for keypress in replay:
            if keypress[3] % 5 == 0:  # 5=> key1, 10 => key2, 15 => both keys
                if keypress[3] != last:
                    if last != 15:  # ignore if the user held both buttons and let go of one
                        keypresses.append(keypress[:3])  # t,x,y
                    last = keypress[3]
            else:
                last = 0
        return keypresses


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
