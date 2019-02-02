import os
from os.path import isfile, join
import pathlib

from secret import API_KEY

PATH_ROOT = pathlib.Path(__file__).parent
PATH_REPLAYS_STUB = PATH_ROOT / "replays"

# get all replays in path to check against
PATH_REPLAYS = [join(PATH_REPLAYS_STUB, f) for f in os.listdir(PATH_REPLAYS_STUB) if isfile(join(PATH_REPLAYS_STUB, f)) and f != ".DS_Store"]

API_BASE = "https://osu.ppy.sh/api/"
API_REPLAY = API_BASE + "get_replay?k=" + API_KEY + "&m=0&b={}&u={}"
API_SCORES_ALL = API_BASE + "get_scores?k=" + API_KEY + "&m=0&b={}&limit={}"
API_SCORES_USER = API_BASE + "get_scores?k=" + API_KEY + "&m=0&b={}&u={}"

            # cookiezi, ryuk,      rafis,     azr8,   toy,
WHITELIST = ["124493", "6304246", "2558286", "2562987", "2757689"]

PATH_DB = PATH_ROOT / "db" / "cache.db" # /absolute/path/db/cache.db

VERSION = "1.0d"
