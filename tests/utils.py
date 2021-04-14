import os
import warnings
from pathlib import Path
from circleguard import Circleguard
from unittest import TestCase

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

class CGTestCase(TestCase):
    @classmethod
    def setUpClass(cls, use_cache=True):
        # pass use_cache=False when we need super precise coordinates for tests
        # to work
        cache_path = Path(__file__).parent / "cache.db"
        cache_path = cache_path if use_cache else None
        cls.cg = Circleguard(KEY, db_path=cache_path)

    def setUp(self):
        # prints TestClassName.testMethodName.
        # See https://stackoverflow.com/a/28745033.
        # later edit: disabled this for now, was getting annoying
        # print(self.id())
        # some weird requests warnings about sockets not getting closed;
        # see https://github.com/psf/requests/issues/3912 for more context and
        # https://github.com/biomadeira/pyPDBeREST/commit/71dfe75859a9086
        # b7e415379702cd61ab61fd6e5
        # for implementation
        warnings.filterwarnings(action="ignore",
                message="unclosed",
                category=ResourceWarning)
