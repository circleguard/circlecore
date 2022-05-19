from datetime import datetime, timezone

from circleguard import (ReplayMap, ReplayPath, RatelimitWeight, Map, User,
    MapUser, Mod, NoInfoAvailableException, ReplayString)

from tests.utils import CGTestCase, RES


class TestReplays(CGTestCase):

    def test_loading_replaypath(self):
        r = ReplayPath(RES / "example_replay.osr")
        self.assertFalse(r.loaded)
        self.cg.load(r)
        self.assertEqual(r.mods, Mod.HD + Mod.DT)
        self.assertEqual(r.replay_id, 2029801532)
        self.assertEqual(r.username, "MarthXT")
        self.assertEqual(r.user_id, 2909663)
        self.assertEqual(r.weight, RatelimitWeight.LIGHT)
        self.assertTrue(r.loaded)
        self.assertEqual(r.beatmap_hash, "c7f9bc1fea826c0f371db08bc5ebc1cc")
        self.assertEqual(r.replay_hash, "266bc8a5f6e9ac0557862da6760388ef")
        self.assertEqual(r.count_300, 154)
        self.assertEqual(r.count_100, 0)
        self.assertEqual(r.count_50, 0)
        self.assertEqual(r.count_geki, 23)
        self.assertEqual(r.count_katu, 0)
        self.assertEqual(r.count_miss, 0)
        self.assertEqual(r.score, 1083482)
        self.assertEqual(r.max_combo, 186)
        self.assertTrue(r.is_perfect_combo)
        self.assertEqual(r.life_bar_graph, None)
        self.assertEqual(r.timestamp, datetime(2015, 12, 16, 19, 40, 39,
            tzinfo=timezone.utc))

    def test_loading_replaymap(self):
        # Toy HDHR score on Pretender
        r = ReplayMap(221777, 2757689)
        self.assertFalse(r.loaded)
        self.cg.load(r)
        self.assertEqual(r.map_id, 221777)
        self.assertEqual(r.user_id, 2757689)
        self.assertEqual(r.mods, Mod.HD + Mod.HR)
        self.assertEqual(r.replay_id, 2832574010)
        self.assertEqual(r.weight, RatelimitWeight.HEAVY)
        self.assertEqual(r.username, "Toy")
        self.assertTrue(r.loaded)
        self.assertEqual(r.count_300, 1449)
        self.assertEqual(r.count_100, 1)
        self.assertEqual(r.count_50, 0)
        self.assertEqual(r.count_geki, 339)
        self.assertEqual(r.count_katu, 1)
        self.assertEqual(r.count_miss, 0)
        self.assertEqual(r.score, 89927731)
        self.assertEqual(r.max_combo, 2388)
        self.assertTrue(r.is_perfect_combo)
        self.assertEqual(r.timestamp, datetime(2019, 6, 19, 3, 22, 44,
            tzinfo=timezone.utc))

    def test_no_replay_raises(self):
        # contrary to loading a Map, where we don't want to raise if the map
        # exists but no scores with the given mod combo exists, we do want to
        # raise if a replay is not available.
        r = ReplayMap(234378, 13947937)
        self.assertRaises(NoInfoAvailableException, lambda: self.cg.load(r))

    def test_no_replay_data_raises(self):
        r = ReplayPath(RES / "other" / "empty_replay_data.osr")
        self.assertRaises(ValueError, lambda: self.cg.load(r))


class TestMap(CGTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.map = Map(221777, "3-5")

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
        # 4rd (kirby mix)
        self.assertEqual(self.map[1].user_id, 9665206)
        # 3rd, 4th, and 5th (toy, kirby mix, rohulk)
        self.assertListEqual([r.user_id for r in self.map[0:3]], [2757689, 9665206, 3219026])
        # 3rd and 5th (toy and rohulk)
        self.assertListEqual([r.user_id for r in self.map[0:3:2]], [2757689, 3219026])

    def test_no_replays_does_not_raise(self):
        # previously, loading the info of a map or user with no scores on the
        # specified mod combination would result in a NoInfoAvailableException
        # being thrown. We want to make sure this doesn't happen.
        m = Map(2245774, "1-2", Mod.NC + Mod.HR + Mod.SO)
        self.cg.load_info(m)
        self.assertEqual(len(m), 0)


class TestUser(CGTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User(124493, span="1-3")
        cls.tybug = cls.cg.User(12092800, "1-10")

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
        # 2nd (FDFD)
        self.assertEqual(self.user[1].map_id, 129891)
        # 1st, 2nd, and 3rd (FDED, FDFD, remote control)
        self.assertListEqual([r.map_id for r in self.user[0:3]], [2249059, 129891, 774965])
        # 1st and 3rd (FDEF, remote control)
        self.assertListEqual([r.map_id for r in self.user[0:3:2]], [2249059, 774965])

    def test_no_replays_does_not_raise(self):
        u = User(12092800, "1-2", Mod.FL + Mod.EZ)
        self.cg.load_info(u)
        self.assertEqual(len(u), 0)

    def test_replay_username_loaded(self):
        # previously, usernames of `ReplayMap`s generated by `User`s would be
        # `None` due to api weirdness. Make sure this doesn't happen.
        self.assertEqual(self.tybug[0].username, "tybug2")


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

class TestReplayString(CGTestCase):
    def test_replay_string_load(self):
        replay_data = open(RES / "example_replay.osr", "rb").read()
        r = ReplayString(replay_data)
        self.cg.load(r)
        self.assertEqual(r.mods, Mod.HD + Mod.DT)
        self.assertEqual(r.replay_id, 2029801532)
        self.assertEqual(r.username, "MarthXT")
        self.assertEqual(r.user_id, 2909663)
        self.assertEqual(r.weight, RatelimitWeight.LIGHT)
        self.assertTrue(r.loaded)


class TestLoadableFromCG(CGTestCase):

    def test_map_from_cg(self):
        m = self.cg.Map(221777, "1-2")
        self.assertTrue(m.info_loaded)
        self.assertFalse(m.loaded)
        self.assertEqual(len(m), 2)

    def test_user_from_cg(self):
        u = self.cg.User(124493, "2, 3-4")
        self.assertTrue(u.info_loaded)
        self.assertFalse(u.loaded)
        self.assertEqual(len(u), 3)

    def test_map_user_from_cg(self):
        mu = self.cg.MapUser(795627, 6304246, "1")
        self.assertTrue(mu.info_loaded)
        self.assertFalse(mu.loaded)
        self.assertEqual(len(mu), 1)


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

        cls.r3 = ReplayPath(RES / "legit" / "legit-1.osr")
        cls.r4 = ReplayPath(RES / "legit" / "legit-1.osr", cache=True)
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
        # loaded == unloaded at the same path is true
        self.cg.load(self.r3)
        self.assertEqual(self.r3, self.r4)
        # loaded == loaded is true regardless of path
        # TODO add test where replay data in the file changes after only one
        # ReplayPath is loaded and ensure the ReplayPaths aren't equal anymore
        self.cg.load(self.r4)
        self.assertEqual(self.r3, self.r4)
