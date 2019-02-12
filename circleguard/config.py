import os
from os.path import isfile, join
import pathlib

from secret import API_KEY

PATH_ROOT = pathlib.Path(__file__).parent
PATH_REPLAYS = PATH_ROOT / "replays"

# names of replays to check
PATH_REPLAYS_USER_STUB = join(PATH_REPLAYS, "user")
PATH_REPLAYS_CHECK_STUB = join(PATH_REPLAYS, "compare") # path of replays to check against

PATH_REPLAYS_USER = [join(PATH_REPLAYS_USER_STUB, f) for f in os.listdir(PATH_REPLAYS_USER_STUB) if isfile(join(PATH_REPLAYS_USER_STUB, f)) and f != ".DS_Store"]
# get all replays in path to check against
PATH_REPLAYS_CHECK = [join(PATH_REPLAYS_CHECK_STUB, f) for f in os.listdir(PATH_REPLAYS_CHECK_STUB) if isfile(join(PATH_REPLAYS_CHECK_STUB, f)) and f != ".DS_Store"]


API_BASE = "https://osu.ppy.sh/api/"
API_REPLAY = API_BASE + "get_replay?k=" + API_KEY + "&m=0&b={}&u={}"
API_SCORES_ALL = API_BASE + "get_scores?k=" + API_KEY + "&m=0&b={}&limit={}"
API_SCORES_USER = API_BASE + "get_scores?k=" + API_KEY + "&m=0&b={}&u={}"

            # cookiezi, ryuk,      rafis,     azr8,   toy,
WHITELIST = ["124493", "6304246", "2558286", "2562987", "2757689"]

PATH_DB = PATH_ROOT / "db" / "cache.db" # /absolute/path/db/cache.db
