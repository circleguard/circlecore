import os
from os.path import isfile, join

from secret import API_KEY


PATH_REPLAYS = os.getcwd() + "/replays/"
PATH_REPLAYS_USER = [PATH_REPLAYS + "user/" + path for path in ["tybug_with_esc.osr"]] # names of replays to check
PATH_REPLAYS_CHECK_STUB = PATH_REPLAYS + "compare/" # path of replays to check against

PATH_REPLAYS_CHECK = [PATH_REPLAYS_CHECK_STUB + f for f in os.listdir(PATH_REPLAYS_CHECK_STUB) if isfile(join(PATH_REPLAYS_CHECK_STUB, f)) and f != ".DS_Store"]

# What portion of a replay to compare, 1.0 checks everything
REPLAY_PORTION = 1

API_BASE = "https://osu.ppy.sh/api/"
API_REPLAY = API_BASE + "get_replay?k=" + API_KEY + "&m=0&b={}&u={}"