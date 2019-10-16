import os
from unittest import TestCase, skip, TestSuite, TextTestRunner
from pathlib import Path
import warnings
from circleguard import (Circleguard, Check, ReplayMap, ReplayPath, Detect, RatelimitWeight, set_options, config,
                        Map)
from circleguard.enums import Mod

KEY = os.environ.get('OSU_API_KEY')
if KEY is None:
    KEY = input("Enter your api key: ")

RES = Path(__file__).parent / "resources"
set_options(loglevel=20)

class CGTestCase(TestCase):
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
    @classmethod
    def setUpClass(cls):
        cls.cg = Circleguard(KEY)

    def test_cheated_replaypath(self):
        # taken from http://redd.it/bvfv8j, remodded replay by same user (CielXDLP) from HDHR to FLHDHR
        replays = [ReplayPath(RES / "stolen_replay1.osr"), ReplayPath(RES / "stolen_replay2.osr")]
        c = Check(replays, detect=Detect.STEAL)
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
        c = Check(replays, detect=Detect.STEAL)
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

class TestOption(CGTestCase):

    SIM_1_2_NO_DETECT = 24
    SIM_1_2_DETECT = 25

    @classmethod
    def setUpClass(cls):
        cls.cg = Circleguard(KEY)
        # TODO use short replays to reduce comparison time (switch to ReplayPaths)
        cls.r1 = ReplayPath(RES / "legit_replay1.osr")
        cls.r2 = ReplayPath(RES / "legit_replay2.osr")
        cls.r3 = ReplayPath(RES / "stolen_replay1.osr")
        cls.cg.load(cls.r1)
        cls.cg.load(cls.r2)
        cls.cg.load(cls.r3)

        # r1 <-> r2 similarity: 24.21291168195734
        # r2 <-> r3 similarity:
        # r3 <-> r1 similarity:

    def setUp(self):
        # reset settings so methods don't interfere with each other's settings
        self.cg = Circleguard(KEY)
        super().setUp()

    def test_steal_thresh_check_true(self):
        set_options(steal_thresh=self.SIM_1_2_NO_DETECT)
        self.cg.set_options(steal_thresh=self.SIM_1_2_NO_DETECT)
        c = Check([self.r1, self.r2], steal_thresh=self.SIM_1_2_DETECT)
        r = list(self.cg.run(c))[0]
        self.assertTrue(r.ischeat, "Thresh should have been set to detect a cheat at the Check level but was not")

    def test_steal_thresh_check_false(self):
        set_options(steal_thresh=self.SIM_1_2_DETECT)
        self.cg.set_options(steal_thresh=self.SIM_1_2_DETECT)
        c = Check([self.r1, self.r2], steal_thresh=self.SIM_1_2_NO_DETECT)
        r = list(self.cg.run(c))[0]
        self.assertFalse(r.ischeat, "Thresh should have been set to miss a cheat at the Check level but was not")

    def test_steal_thresh_check_without_class_true(self):
        set_options(steal_thresh=self.SIM_1_2_NO_DETECT)
        c = Check([self.r1, self.r2], steal_thresh=self.SIM_1_2_DETECT)
        r = list(self.cg.run(c))[0]
        self.assertTrue(r.ischeat, "Thresh should have been set to detect a cheat at the Check level but was not")

    def test_steal_thresh_check_without_class_false(self):
        set_options(steal_thresh=self.SIM_1_2_DETECT)
        c = Check([self.r1, self.r2], steal_thresh=self.SIM_1_2_NO_DETECT)
        r = list(self.cg.run(c))[0]
        self.assertFalse(r.ischeat, "Thresh should have been set to miss a cheat at the Check level but was not")

    def test_steal_thresh_check_without_class_or_global_true(self):
        c = Check([self.r1, self.r2], steal_thresh=self.SIM_1_2_DETECT)
        r = list(self.cg.run(c))[0]
        self.assertTrue(r.ischeat, "Thresh should have been set to detect a cheat at the Check level but was not")

    def test_steal_thresh_check_without_class_or_global_false(self):
        c = Check([self.r1, self.r2], steal_thresh=self.SIM_1_2_NO_DETECT)
        r = list(self.cg.run(c))[0]
        self.assertFalse(r.ischeat, "Thresh should have been set to miss a cheat at the Check level but was not")


    def test_steal_thresh_class_true(self):
        set_options(steal_thresh=self.SIM_1_2_NO_DETECT)
        self.cg.set_options(steal_thresh=self.SIM_1_2_DETECT)
        c = Check([self.r1, self.r2])
        r = list(self.cg.run(c))[0]
        self.assertTrue(r.ischeat, "Thresh should have been set to detect a cheat at the class level but was not")

    def test_steal_thresh_class_false(self):
        set_options(steal_thresh=self.SIM_1_2_DETECT)
        self.cg.set_options(steal_thresh=self.SIM_1_2_NO_DETECT)
        c = Check([self.r1, self.r2])
        r = list(self.cg.run(c))[0]
        self.assertFalse(r.ischeat, "Thresh should have been set to miss a cheat at the class level but was not")

    def test_steal_thresh_class_without_global_true(self):
        self.cg.set_options(steal_thresh=self.SIM_1_2_DETECT)
        c = Check([self.r1, self.r2])
        r = list(self.cg.run(c))[0]
        self.assertTrue(r.ischeat, "Thresh should have been set to detect a cheat at the class level but was not")

    def test_steal_thresh_class_without_global_false(self):
        self.cg.set_options(steal_thresh=self.SIM_1_2_NO_DETECT)
        c = Check([self.r1, self.r2])
        r = list(self.cg.run(c))[0]
        self.assertFalse(r.ischeat, "Thresh should have been set to miss a cheat at the class level but was not")

    # TODO test all options, not just steal thresh

class TestInclude(CGTestCase):
    @classmethod
    def setUpClass(cls):
        cls.cg = Circleguard(KEY)


    def test_include_replaypath_filter_some(self):
        def _include(replay):
            return replay.replay_id in [2801164636]

        c = Check([ReplayPath(RES / "stolen_replay1.osr"), ReplayPath(RES / "stolen_replay2.osr")], include=_include)
        self.cg.load(c)
        c.filter(self.cg.loader)
        self.assertEqual(len(c.all_replays()), 1, "A replay should have been filtered out but it was not")

    def test_include_replaypath_filter_none(self):
        c = Check([ReplayPath(RES / "stolen_replay1.osr"), ReplayPath(RES / "stolen_replay2.osr")])
        self.cg.load(c)
        c.filter(self.cg.loader)
        self.assertEqual(len(c.all_replays()), 2, "No replays should have been filtered but at least one was")

    def test_include_replaypath_filter_all(self):
        def _include(replay):
            return False
        c = Check([ReplayPath(RES / "stolen_replay1.osr"), ReplayPath(RES / "stolen_replay2.osr")], include=_include)
        self.cg.load(c)
        c.filter(self.cg.loader)
        self.assertEqual(len(c.all_replays()), 0, "All replays should have been filtered but at least one was not")

class TestMap(CGTestCase):
    @classmethod
    def setUpClass(cls):
        cls.cg = Circleguard(KEY)


    def test_map_alone(self):
        m = Map(129891, num=2) # Freedom Dive [Four Dimensions]
        c = Check([m], detect=Detect.STEAL)
        r = list(self.cg.run(c))
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].earlier_replay.mods, Mod.HD + Mod.HR) # cookiezi HDHR

    def test_map_with_replaypath(self):
        m = Map(129891, num=1)
        rpath = ReplayPath(RES / "legit_replay1.osr")
        # of course, it makes no sense to compare replays on two different maps
        # for steals, but it serves this tests' purpose.
        c = Check([m, rpath], detect=Detect.STEAL)
        r = list(self.cg.run(c))
        self.assertEqual(len(r), 1)
        # dont need a ton of checks here, mostly just checking that
        # running with Map and Replay combined *runs*. Other tests ensure
        # the accuracy of the Results
        self.assertEqual(r[0].later_replay.username, "chocomint")
        self.assertEqual(r[0].earlier_replay.username, "Crissinop")

    def test_map_with_replaymap(self):
        m = Map(129891, num=1)
        rmap = ReplayMap(1524183, 4196808) # Karthy HDHR on Full Moon
        c = Check([m, rmap], detect=Detect.STEAL)
        r = list(self.cg.run(c))
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].later_replay.username, "Karthy")
        self.assertEqual(r[0].earlier_replay.username, "chocomint")

    def test_map_with_replaypath_replaymap(self):
        m = Map(129891, num=1)
        rpath = ReplayPath(RES / "legit_replay1.osr")
        rmap = ReplayMap(1524183, 4196808) # Karthy HDHR on Full Moon
        c = Check([m, rmap, rpath], detect=Detect.STEAL)
        r = list(self.cg.run(c))
        self.assertEqual(len(r), 3)

# if __name__ == '__main__':
    # suite = TestSuite()
    # suite.addTest(TestReplays("test_loading_replaymap"))
    # suite.addTest(TestMap("test_map_with_replaymap"))
    # suite.addTest(TestMap("test_map_with_replaypath_replaymap"))

    # TextTestRunner().run(suite)
