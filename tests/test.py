import os
from unittest import TestCase, skip, TestSuite, TextTestRunner
from pathlib import Path
import warnings
from circleguard import (Circleguard, Check, ReplayMap, ReplayPath, Detect,
                         RatelimitWeight, set_options, Map, User, MapUser, Mod,
                         Loader, InvalidKeyException)

KEY = os.environ.get('OSU_API_KEY')
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
        r = list(self.cg.steal_check(replays))
        self.assertEqual(len(r), 1, f"{len(r)} results returned instead of 1")
        r = r[0]
        self.assertTrue(r.similarity < 18, "Cheated replays were not detected as cheated")

        r1 = r.replay1
        r2 = r.replay2
        earlier = r.earlier_replay
        later = r.later_replay

        self.assertAlmostEqual(r.similarity, 2.19236, delta=DELTA, msg="Similarity is not correct")
        self.assertEqual(r1.map_id, r2.map_id, "Replay map ids did not match")
        self.assertEqual(r1.map_id, 1988753, "Replay map id was not correct")
        self.assertEqual(earlier.mods, Mod.HD + Mod.HR, "Earlier replay mods was not correct")
        self.assertEqual(later.mods, Mod.FL + Mod.HD + Mod.HR, "Later replay mods was not correct")
        self.assertEqual(earlier.replay_id, 2801164636, "Earlier replay id was not correct")
        self.assertEqual(later.replay_id, 2805164683, "Later replay id was not correct")
        self.assertEqual(r1.username, r2.username, "Replay usernames did not match")

    def test_legitimate_replaypath(self):
        replays = [ReplayPath(RES / "legit_replay1.osr"), ReplayPath(RES / "legit_replay2.osr")]
        r = list(self.cg.steal_check(replays))
        self.assertEqual(len(r), 1, f"{len(r)} results returned instead of 1")
        r = r[0]
        self.assertFalse(r.similarity < 18, "Legitimate replays were detected as stolen")

        r1 = r.replay1
        r2 = r.replay2
        earlier = r.earlier_replay
        later = r.later_replay

        self.assertAlmostEqual(r.similarity, 23.03593, delta=DELTA, msg="Similarity is not correct")
        self.assertEqual(r1.map_id, r2.map_id, "Replay map ids did not match")
        self.assertEqual(r1.map_id, 722238, "Replay map id was not correct")
        self.assertEqual(earlier.mods, Mod.HD + Mod.NC, "Earlier replay mods was not correct")
        self.assertEqual(later.mods, Mod.HD + Mod.DT, "Later replay mods was not correct")
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

    def test_num_invariance(self):
        replays = [ReplayPath(RES / "stolen_replay1.osr"), ReplayPath(RES / "stolen_replay2.osr"),
                   ReplayPath(RES / "legit_replay1.osr"), ReplayPath(RES / "legit_replay2.osr")]

        for num in range(2, 5):
            r = list(self.cg.steal_check(replays[:num]))
            results_num = num * (num - 1) / 2 #n choose k formula with k=2
            self.assertEqual(len(r), results_num, f"{len(r)} results returned instead of {results_num}")
            r = r[0]
            self.assertTrue(r.similarity < 18, f"Cheated replays were not detected as cheated at num {num}")

            r1 = r.replay1
            r2 = r.replay2
            earlier = r.earlier_replay
            later = r.later_replay

            self.assertAlmostEqual(r.similarity, 2.19236, delta=DELTA, msg=f"Similarity is not correct at num {num}")
            self.assertEqual(r1.map_id, r2.map_id, f"Replay map ids did not match at num {num}")
            self.assertEqual(r1.map_id, 1988753, f"r1 map id was not correct at num {num}")
            self.assertEqual(earlier.mods, Mod.HD + Mod.HR, f"Earlier replay mods was not correct at num {num}")
            self.assertEqual(later.mods, Mod.FL + Mod.HD + Mod.HR, f"Later replay mods was not correct at num {num}")
            self.assertEqual(earlier.replay_id, 2801164636, f"Earlier replay id was not correct at num {num}")
            self.assertEqual(later.replay_id, 2805164683, f"Later replay id was not correct at num {num}")
            self.assertEqual(r1.username, r2.username, f"Replay usernames did not match at num {num}")

class TestCorrection(CGTestCase):
    @classmethod
    def setUpClass(cls):
        cls.cg = Circleguard(KEY)
        cls.r1 = ReplayPath(RES / "corrected_replay1.osr")

    def test_cheated_replay(self):
        r = list(self.cg.correction_check(self.r1))[0]
        snaps = r.snaps

        self.assertEqual(len(snaps), 15)
        # beginning
        self.assertEqual(snaps[0].time, 5103)
        self.assertAlmostEqual(snaps[0].angle, 7.38491, delta=DELTA)
        self.assertAlmostEqual(snaps[0].distance, 16.69009, delta=DELTA)
        # middle
        self.assertEqual(snaps[8].time, 71652)
        self.assertAlmostEqual(snaps[8].angle, 6.34890, delta=DELTA)
        self.assertAlmostEqual(snaps[8].distance, 27.59918, delta=DELTA)
        # end
        self.assertEqual(snaps[14].time, 79052)
        self.assertAlmostEqual(snaps[14].angle, 8.77141, delta=DELTA)
        self.assertAlmostEqual(snaps[14].distance, 8.21841, delta=DELTA)


class TestMap(CGTestCase):
    @classmethod
    def setUpClass(cls):
        cls.cg = Circleguard(KEY)
        cls.map = Map(221777, "1-3")

    def test_map_load(self):
        self.assertEqual(len(self.map.all_replays()), 0)
        self.assertEqual(len(self.map[:]), 0)
        self.assertFalse(self.map.loaded)
        self.assertFalse(self.map.info_loaded)

        self.cg.load_info(self.map)
        self.assertFalse(self.map.loaded)
        self.assertTrue(self.map.info_loaded)
        self.assertEqual(len(self.map.all_replays()), 3)
        self.assertEqual(len(self.map[:]), 3)

        self.cg.load(self.map)
        self.assertTrue(self.map.loaded)
        self.assertTrue(self.map.info_loaded)

    def test_map_slice(self):
        # sanity check (map id better be what we put in)
        self.assertEqual(self.map[0].map_id, 221777)
        # 2nd (rohulk)
        self.assertEqual(self.map[1].user_id, 3219026)
        # 1st, 2nd, and 3rd (toy, rohulk, epiphany)
        self.assertListEqual([r.user_id for r in self.map[0:3]], [2757689, 3219026, 3256299])
        # 1st and 3rd (toy and epiphany)
        self.assertListEqual([r.user_id for r in self.map[0:3:2]], [2757689, 3256299])


class TestUser(CGTestCase):
    @classmethod
    def setUpClass(cls):
        cls.cg = Circleguard(KEY)
        cls.user = User(124493, span="1-3")

    def test_user_load(self):
        self.assertEqual(len(self.user.all_replays()), 0)
        self.assertEqual(len(self.user[:]), 0)
        self.assertFalse(self.user.loaded)
        self.assertFalse(self.user.info_loaded)

        self.cg.load_info(self.user)
        self.assertFalse(self.user.loaded)
        self.assertTrue(self.user.info_loaded)
        self.assertEqual(len(self.user.all_replays()), 3)
        self.assertEqual(len(self.user[:]), 3)
        self.cg.load(self.user)
        self.assertTrue(self.user.loaded)
        self.assertTrue(self.user.info_loaded)

    def test_user_slice(self):
        # sanity check (user id better be what we put in)
        self.assertEqual(self.user[0].user_id, 124493)
        # 2nd (Everything will Freeze)
        self.assertEqual(self.user[1].map_id, 555797)
        # 1st, 2nd, and 3rd (FDFD, Everything will Freeze, and Remote Control)
        self.assertListEqual([r.map_id for r in self.user[0:3]], [129891, 555797, 774965])
        # 1st and 3rd (FDFD and Remote Control)
        self.assertListEqual([r.map_id for r in self.user[0:3:2]], [129891, 774965])


class TestMapUser(CGTestCase):
    @classmethod
    def setUpClass(cls):
        cls.cg = Circleguard(KEY)
        cls.mu = MapUser(795627, 6304246, span="1-2")

    def test_map_user_load(self):
        self.assertEqual(len(self.mu.all_replays()), 0)
        self.assertEqual(len(self.mu[:]), 0)
        self.assertFalse(self.mu.loaded)
        self.assertFalse(self.mu.info_loaded)

        self.cg.load_info(self.mu)
        self.assertFalse(self.mu.loaded)
        self.assertTrue(self.mu.info_loaded)
        self.assertEqual(len(self.mu.all_replays()), 2)
        self.assertEqual(len(self.mu[:]), 2)

        self.cg.load(self.mu)
        self.assertTrue(self.mu.loaded)
        self.assertTrue(self.mu.info_loaded)

    def test_map_user_slice(self):
        # sanity checks (user and map id better be what we put in)
        self.assertEqual(self.mu[0].user_id, 6304246)
        self.assertEqual(self.mu[1].user_id, 6304246)
        self.assertEqual(self.mu[0].map_id, 795627)
        self.assertEqual(self.mu[1].map_id, 795627)
        # test slicing
        self.assertListEqual([r.map_id for r in self.mu[0:2]], [795627, 795627])


class TestLoader(CGTestCase):
    @classmethod
    def setUpClass(cls):
        cls.loader = Loader(KEY)

    def test_loading_map_id(self):
        result = self.loader.map_id("E")
        self.assertEqual(result, 0)

        result = self.loader.map_id("9d0a8fec2fe3f778334df6bdc60b113c")
        self.assertEqual(result, 221777)

    def test_loading_user_id(self):
        result = self.loader.user_id("E")
        self.assertEqual(result, 0)

        result = self.loader.user_id("] [")
        self.assertEqual(result, 13506780)

        result = self.loader.user_id("727")
        self.assertEqual(result, 10750899)

    def test_loading_username(self):
        result = self.loader.username(0)
        self.assertEqual(result, "")

        result = self.loader.username(13506780)
        self.assertEqual(result, "] [")

    def test_incorrect_key(self):
        loader = Loader("incorrect key")
        self.assertRaises(InvalidKeyException, loader.username, 13506780)
        self.assertRaises(InvalidKeyException, loader.user_id, "] [")
        self.assertRaises(InvalidKeyException, loader.map_id, "9d0a8fec2fe3f778334df6bdc60b113c")

class TestEquality(CGTestCase):
    @classmethod
    def setUpClass(cls):
        cls.cg = Circleguard(KEY)

        cls.user = User(2757689, "1-2") # toy, #1=sidetracked day, #2=View of The River Styx
        cls.user1 = User(2757689, "1-2", cache=False)
        cls.user2 = User(2757689, "1-2", mods=Mod.HT)
        cls.user3 = User(2757689, "1")

        cls.map = Map(1754777, "1-4") #sidetracked day: umbre, karthy, -duckleader-, toy
        cls.map1 = Map(1754777, "1-4", cache=False)
        cls.map2 = Map(1754777, "1-4", mods=Mod.HD)
        cls.map3 = Map(1754777, "1-2")

        cls.r = ReplayMap(1754777, 2766034) # umbre +HDHR on sidetracked day
        cls.r1 = ReplayMap(1754777, 2766034, cache=True)
        cls.r2 = ReplayMap(1754777, 2766034, mods=Mod.NF)

        cls.r3 = ReplayPath(RES / "legit_replay1.osr")
        cls.r4 = ReplayPath(RES / "legit_replay1.osr", cache=True)
        cls.r5 = ReplayPath(RES / "stolen_replay1.osr")

        cls.cg.load_info(cls.user)
        cls.cg.load_info(cls.user1)
        cls.cg.load_info(cls.user2)

        cls.cg.load_info(cls.map)
        cls.cg.load_info(cls.map1)
        cls.cg.load_info(cls.map2)

    def test_equality_user(self):
        self.assertEqual(self.user, self.user1)
        self.assertNotEqual(self.user, self.user2)
        self.assertNotEqual(self.user, self.user3)

    def test_equality_map(self):
        self.assertEqual(self.map, self.map1)
        self.assertNotEqual(self.map, self.map2)
        self.assertNotEqual(self.map, self.map3)

    def test_equality_replaymap(self):
        self.assertEqual(self.r, self.r1)
        self.assertNotEqual(self.r, self.r2)

    def test_equality_replaypath(self):
        self.assertEqual(self.r3, self.r4)
        self.assertNotEqual(self.r3, self.r5)


if __name__ == '__main__':
    suite = TestSuite()
    suite.addTest(TestMap("test_map_with_replays"))

    TextTestRunner().run(suite)
