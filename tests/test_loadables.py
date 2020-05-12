from unittest import skip, TestSuite, TextTestRunner
from circleguard import (Circleguard, Check, ReplayMap, ReplayPath, Detect,
                         RatelimitWeight, set_options, Map, User, MapUser, Mod,
                         Loader, InvalidKeyException)

from tests.utils import CGTestCase, RES


class TestReplays(CGTestCase):

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
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        super().setUpClass()
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
        super().setUpClass()
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


class TestEquality(CGTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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
