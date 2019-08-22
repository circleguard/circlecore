from unittest import TestCase
from pathlib import Path

from circleguard import Circleguard, Check, ReplayMap, ReplayPath, Detect, RatelimitWeight, set_options

KEY = input("Enter your api key: ")
RES = Path(__file__).parent / "resources"
set_options(loglevel=20)

def log(function):
    def wrapper(*args, **kwargs):
        print(f"Running test {function.__name__}")
        return function(*args, **kwargs)
    return wrapper


class TestReplays(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cg = Circleguard(KEY)

    @log
    def test_cheated_replay(self):
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
        self.assertEqual(earlier.mods, 24, "Earlier replay mods was not correct") # HDHR
        self.assertEqual(later.mods, 1048, "Later replay mods was not correct") # FLHDHR
        self.assertEqual(earlier.replay_id, 2801164636, "Earlier replay id was not correct")
        self.assertEqual(later.replay_id, 2805164683, "Later replay id was not correct")
        self.assertEqual(r1.username, r2.username, "Replay usernames did not match")

    @log
    def test_legitimate_replay(self):
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
        self.assertEqual(earlier.mods, 584, "Earlier replay mods was not correct") # HDNC
        self.assertEqual(later.mods, 72, "Later replay mods was not correct") # HDDT
        self.assertEqual(earlier.replay_id, 2157431869, "Earlier replay id was not correct")
        self.assertEqual(later.replay_id, 2309618113, "Later replay id was not correct")
        self.assertEqual(earlier.username, "Crissinop", "Earlier username was not correct")
        self.assertEqual(later.username, "TemaZpro", "Later username was not correct")

    @log
    def test_loading_replaypath(self):
        r = ReplayPath(RES / "example_replay.osr")
        self.assertFalse(r.loaded, "Loaded status was not correct")
        self.cg.load(r)
        self.assertEqual(r.mods, 72, "Mods was not correct")
        self.assertEqual(r.replay_id, 2029801532, "Replay id was not correct")
        self.assertEqual(r.username, "MarthXT", "Username was not correct")
        self.assertEqual(r.user_id, 2909663, "User id was not correct")
        self.assertEqual(r.weight, RatelimitWeight.LIGHT, "RatelimitWeight was not correct")
        self.assertTrue(r.loaded, "Loaded status was not correct")

    @log
    def test_loading_replaymap(self):
        # Toy HDHR score on Pretender
        r = ReplayMap(221777, 2757689)
        self.assertFalse(r.loaded, "Loaded status was not correct")
        self.cg.load(r)
        self.assertEqual(r.map_id, 221777, "Map id was not correct")
        self.assertEqual(r.user_id, 2757689, "Map id was not correct")
        self.assertEqual(r.mods, 24, "Mods was not correct")
        self.assertEqual(r.replay_id, 2832574010, "Replay is was not correct")
        self.assertEqual(r.weight, RatelimitWeight.HEAVY, "RatelimitWeight was not correct")
        self.assertEqual(r.username, "Toy", "Username was not correct")
        self.assertTrue(r.loaded, "Loaded status was not correct")



class TestOption(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cg = Circleguard(KEY)
        cls.r1 = ReplayMap(221777, 2757689)
        cls.r2 = ReplayMap(221777, 3219026)
        cls.r3 = ReplayMap(221777, 3256299)
        cls.cg.load(cls.r1)
        cls.cg.load(cls.r2)
        cls.cg.load(cls.r3)

        # r1 <-> r2 similarity: 20.875089740385583
        # r2 <-> r3 similarity:
        # r3 <-> r1 similarity:

    def setUp(self):
        # reset settings so methods don't interfere with each other's settings
        self.cg = Circleguard(KEY)

    @log
    def test_steal_thresh_check_true(self):
        set_options(steal_thresh=19)
        self.cg.set_options(steal_thresh=19)
        c = Check([self.r1, self.r2], steal_thresh=21)
        r = list(self.cg.run(c))[0]
        self.assertTrue(r.ischeat, "Thresh should have been set to detect a cheat at the Check level but was not")

    @log
    def test_steal_thresh_check_false(self):
        set_options(steal_thresh=21)
        self.cg.set_options(steal_thresh=21)
        c = Check([self.r1, self.r2], steal_thresh=19)
        r = list(self.cg.run(c))[0]
        self.assertFalse(r.ischeat, "Thresh should have been set to miss a cheat at the Check level but was not")

    @log
    def test_steal_thresh_check_without_class_true(self):
        set_options(steal_thresh=19)
        c = Check([self.r1, self.r2], steal_thresh=21)
        r = list(self.cg.run(c))[0]
        self.assertTrue(r.ischeat, "Thresh should have been set to detect a cheat at the Check level but was not")

    @log
    def test_steal_thresh_check_without_class_false(self):
        set_options(steal_thresh=21)
        c = Check([self.r1, self.r2], steal_thresh=19)
        r = list(self.cg.run(c))[0]
        self.assertFalse(r.ischeat, "Thresh should have been set to miss a cheat at the Check level but was not")

    @log
    def test_steal_thresh_check_without_class_or_global_true(self):
        c = Check([self.r1, self.r2], steal_thresh=21)
        r = list(self.cg.run(c))[0]
        self.assertTrue(r.ischeat, "Thresh should have been set to detect a cheat at the Check level but was not")

    def test_steal_thresh_check_without_class_or_global_false(self):
        c = Check([self.r1, self.r2], steal_thresh=19)
        r = list(self.cg.run(c))[0]
        self.assertFalse(r.ischeat, "Thresh should have been set to miss a cheat at the Check level but was not")


    @log
    def test_steal_thresh_class_true(self):
        set_options(steal_thresh=19)
        self.cg.set_options(steal_thresh=21)
        c = Check([self.r1, self.r2])
        r = list(self.cg.run(c))[0]
        self.assertTrue(r.ischeat, "Thresh should have been set to detect a cheat at the class level but was not")

    @log
    def test_steal_thresh_class_false(self):
        set_options(steal_thresh=21)
        self.cg.set_options(steal_thresh=19)
        c = Check([self.r1, self.r2])
        r = list(self.cg.run(c))[0]
        self.assertFalse(r.ischeat, "Thresh should have been set to miss a cheat at the class level but was not")

    @log
    def test_steal_thresh_class_without_global_true(self):
        self.cg.set_options(steal_thresh=21)
        c = Check([self.r1, self.r2])
        r = list(self.cg.run(c))[0]
        self.assertTrue(r.ischeat, "Thresh should have been set to detect a cheat at the class level but was not")

    @log
    def test_steal_thresh_class_without_global_false(self):
        self.cg.set_options(steal_thresh=19)
        c = Check([self.r1, self.r2])
        r = list(self.cg.run(c))[0]
        self.assertFalse(r.ischeat, "Thresh should have been set to miss a cheat at the class level but was not")
