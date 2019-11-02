import os
from unittest import TestCase, skip, TestSuite, TextTestRunner
from pathlib import Path
import warnings
from circleguard import (Circleguard, Check, ReplayMap, ReplayPath, RelaxDetect, StealDetect,
                         RatelimitWeight, set_options, Map, User, Mod)

KEY = os.environ.get('OSU_API_KEY')
if KEY is None:
    KEY = input("Enter your api key: ")

RES = Path(__file__).parent / "resources"
set_options(loglevel=20)

# how many times our test cases hits the get_replay endpoint.
# Keep this below a multiple of 10 (preferably at most 9) so tests run in a reasonable amount of time.
# We may want to split tests into "heavy" and "light" where light loads <10 heavy calls and heavy loads as many as we need.
# light can run locally, heavy can run on prs.
HEAVY_CALL_COUNT = 6

class CGTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cg = Circleguard(KEY)

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

class TestReplays(CGTestCase):

    def test_cheated_replaypath(self):
        # taken from http://redd.it/bvfv8j, remodded replay by same user (CielXDLP) from HDHR to FLHDHR
        replays = [ReplayPath(RES / "stolen_replay1.osr"), ReplayPath(RES / "stolen_replay2.osr")]
        c = Check(replays, detect=StealDetect(18))
        r = list(self.cg.run(c))
        self.assertEqual(len(r), 1, f"{len(r)} results returned instead of 1")
        r = r[0]
        self.assertTrue(r.ischeat, "Cheated replays were not detected as cheated")

        r1 = r.replay1
        r2 = r.replay2
        earlier = r.earlier_replay
        later = r.later_replay

        self.assertAlmostEqual(r.similarity, 4.2608, delta=0.0001, msg="Similarity is not correct")
        self.assertEqual(r1.map_id, r2.map_id, "Replay map ids did not match")
        self.assertEqual(r1.map_id, 1988753, "Replay map id was not correct")
        self.assertEqual(earlier.mods, Mod.HD + Mod.HR, "Earlier replay mods was not correct") # HDHR
        self.assertEqual(later.mods, Mod.FL + Mod.HD + Mod.HR, "Later replay mods was not correct") # FLHDHR
        self.assertEqual(earlier.replay_id, 2801164636, "Earlier replay id was not correct")
        self.assertEqual(later.replay_id, 2805164683, "Later replay id was not correct")
        self.assertEqual(r1.username, r2.username, "Replay usernames did not match")

    def test_legitimate_replaypath(self):
        replays = [ReplayPath(RES / "legit_replay1.osr"), ReplayPath(RES / "legit_replay2.osr")]
        c = Check(replays, detect=StealDetect(18))
        r = list(self.cg.run(c))
        self.assertEqual(len(r), 1, f"{len(r)} results returned instead of 1")
        r = r[0]
        self.assertFalse(r.ischeat, "Legitimate replays were detected as stolen")

        r1 = r.replay1
        r2 = r.replay2
        earlier = r.earlier_replay
        later = r.later_replay

        self.assertAlmostEqual(r.similarity, 24.2129, delta=0.0001, msg="Similarity is not correct")
        self.assertEqual(r1.map_id, r2.map_id, "Replay map ids did not match")
        self.assertEqual(r1.map_id, 722238, "Replay map id was not correct")
        self.assertEqual(earlier.mods, Mod.HD + Mod.NC, "Earlier replay mods was not correct") # HDNC
        self.assertEqual(later.mods, Mod.HD + Mod.DT, "Later replay mods was not correct") # HDDT
        self.assertEqual(earlier.replay_id, 2157431869, "Earlier replay id was not correct")
        self.assertEqual(later.replay_id, 2309618113, "Later replay id was not correct")
        self.assertEqual(earlier.username, "Crissinop", "Earlier username was not correct")
        self.assertEqual(later.username, "TemaZpro", "Later username was not correct")

    def test_loading_replaypath(self):
        r = ReplayPath(RES / "example_replay.osr")
        self.assertFalse(r.loaded, "Loaded status was not correct")
        self.cg.load(r)
        self.assertEqual(r.mods, Mod.HD + Mod.DT, "Mods was not correct")
        self.assertEqual(r.replay_id, 2029801532, "Replay id was not correct")
        self.assertEqual(r.username, "MarthXT", "Username was not correct")
        self.assertEqual(r.user_id, 2909663, "User id was not correct")
        self.assertEqual(r.weight, RatelimitWeight.LIGHT, "RatelimitWeight was not correct")
        self.assertTrue(r.loaded, "Loaded status was not correct")

    def test_loading_replaymap(self):
        # Toy HDHR score on Pretender
        r = ReplayMap(221777, 2757689)
        self.assertFalse(r.loaded, "Loaded status was not correct")
        self.cg.load(r)
        self.assertEqual(r.map_id, 221777, "Map id was not correct")
        self.assertEqual(r.user_id, 2757689, "Map id was not correct")
        self.assertEqual(r.mods, Mod.HD + Mod.HR, "Mods was not correct")
        self.assertEqual(r.replay_id, 2832574010, "Replay is was not correct")
        self.assertEqual(r.weight, RatelimitWeight.HEAVY, "RatelimitWeight was not correct")
        self.assertEqual(r.username, "Toy", "Username was not correct")
        self.assertTrue(r.loaded, "Loaded status was not correct")



class TestMap(CGTestCase):

    def test_map_alone(self):
        m = Map(129891, num=1) # Freedom Dive [Four Dimensions]
        c = Check([m], RelaxDetect(18))
        r = list(self.cg.run(c))
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].replay.mods, Mod.HD + Mod.HR) # cookiezi HDHR

    def test_map_with_replays(self):
        m = Map(129891, num=1)
        rpath = ReplayPath(RES / "legit_replay1.osr")
        rmap = ReplayMap(1524183, 4196808) # Karthy HDHR on Full Moon
        # of course, it makes no sense to compare replays on two different maps
        # for steals, but it serves this test's purpose.
        c = Check([m, rpath, rmap], RelaxDetect(18))
        r = list(self.cg.run(c))
        self.assertEqual(len(r), 3)
        # dont need a ton of checks here, mostly just checking that
        # running with Map and Replay combined *runs*. Other tests ensure
        # the accuracy of the Results
        self.assertAlmostEqual(r[0].ur, 65.769, places=2)
        self.assertAlmostEqual(r[1].ur, 100.104, places=2)
        self.assertAlmostEqual(r[2].ur, 68.518, places=2)




class TestUser(CGTestCase):
    @classmethod
    def setUpClass(cls):
        cls.cg = Circleguard(KEY)
        cls.user = User(124493, num=3)

    def test_user_load(self):
        self.assertEqual(len(self.user.all_replays()), 0)
        self.assertEqual(len(self.user[:]), 0)
        self.cg.load_info(self.user)
        self.assertEqual(len(self.user.all_replays()), 3)
        self.assertEqual(len(self.user[:]), 3)
        self.cg.load(self.user)

    def test_user_slice(self):
        # 2nd (Everything will Freeze)
        self.assertEqual(self.user[1].map_id, 555797)
        # 1st, 2nd, and 3rd (FDFD, Everything will Freeze, and Remote Control)
        self.assertListEqual([r.map_id for r in self.user[0:3]], [129891, 555797, 774965])
        # 1st and 3rd (FDFD and Remote Control)
        self.assertListEqual([r.map_id for r in self.user[0:3:2]], [129891, 774965])
        self.assertEqual(self.user[0].map_id, 129891)

if __name__ == '__main__':
    suite = TestSuite()
    suite.addTest(TestMap("test_map_with_replays"))

    TextTestRunner().run(suite)
