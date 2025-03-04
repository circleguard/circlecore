import os
from pathlib import Path

from circleguard import Circleguard, Loader

KEY = os.environ.get("OSU_API_KEY")
if not KEY:
    KEY = input("Enter your api key: ")

RES = Path(__file__).parent / "resources"
# disabled for now
# set_options(loglevel=20)

# what precision we want to guarantee for our tests
DELTA = 0.00001
# osu! only shows ur to two decimals, so we only guarantee precision to there
UR_DELTA = 0.01
# threshold for frametime
FRAMETIME_LIMIT = 13


cg = Circleguard(KEY, db_path=Path(__file__).parent / "cache.db")
cg_no_cache = Circleguard(KEY)
loader = Loader(KEY)
