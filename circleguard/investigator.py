from osu_parser.osu_parser.beatmap import Beatmap
import numpy as np

class Investigator:
    """
    A class for checking isolated replays for cheats.

    See Also:
        Comparer
    """
    def __init__(self, replay, beatmap_dir=""):
        self.replay = replay.as_list_with_timestamps()
        if beatmap_dir:
            self.beatmap = Beatmap(beatmap_dir)
        else:
            self.beatmap = None

    def calculate_ur(self):
        hitobjs = self._parse_beatmap(self.beatmap)
        keypresses = self._parse_keys(self.beatmap)
        diff = []

        # remove hits not near hitobj
        hitwindow = 150 + 50 * (5 - self.beatmap.difficulty["OverallDifficulty"]) / 5
        # inefficient as fugg, but not important rn
        for i in keypresses:
            for j in hitobjs:
                if i > j-(hitwindow/2) and i < j+(hitwindow/2):
                    diff = j-i
                    diff.append(diff)

        return np.std(diff)*10

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