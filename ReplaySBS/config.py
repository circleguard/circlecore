import os
from os.path import isfile, join
import pathlib

#from secret import API_KEY
API_KEY = ""

PATH_REPLAYS = pathlib.Path(__file__).parent / "replays"

# names of replays to check
PATH_REPLAYS_USER = [join(PATH_REPLAYS, "user", path) for path in ["woey.osr"]]
PATH_REPLAYS_CHECK_STUB = join(PATH_REPLAYS, "compare") # path of replays to check against

# get all replays in path to check against
PATH_REPLAYS_CHECK = [join(PATH_REPLAYS_CHECK_STUB, f) for f in os.listdir(PATH_REPLAYS_CHECK_STUB) if isfile(join(PATH_REPLAYS_CHECK_STUB, f)) and f != ".DS_Store"]


API_BASE = "https://osu.ppy.sh/api/"
API_REPLAY = API_BASE + "get_replay?k=" + API_KEY + "&m=0&b={}&u={}"
API_SCORES = API_BASE + "get_scores?k=" + API_KEY + "&m=0&b={}"
