import os
import warnings
from pathlib import Path
from circleguard import Circleguard, set_options
from unittest import TestCase

KEY = os.environ.get("OSU_API_KEY")
if not KEY:
    KEY = input("Enter your api key: ")

RES = Path(__file__).parent / "resources"
set_options(loglevel=20)

# what precision we want to guarantee for our tests
DELTA = 0.00001
# how many times our test cases hits the get_replay endpoint.
# Keep this below a multiple of 10 (preferably at most 9) so tests run in a reasonable amount of time.
# We may want to split tests into "heavy" and "light" where light loads <10 heavy calls and heavy loads as many as we need.
# light can run locally, heavy can run on prs.
HEAVY_CALL_COUNT = 9

class CGTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cache_path = Path(__file__).parent / "cache.db"
        cls.cg = Circleguard(KEY, db_path=cache_path)

    def setUp(self):
        # prints TestClassName.testMethodName.
        # See https://stackoverflow.com/a/28745033
        print(self.id())
        # some weird requests warnings about sockets not getting closed;
        # see https://github.com/psf/requests/issues/3912 for more context and
        # https://github.com/biomadeira/pyPDBeREST/commit/71dfe75859a9086b7e415379702cd61ab61fd6e5 for implementation
        warnings.filterwarnings(action="ignore",
                message="unclosed",
                category=ResourceWarning)
