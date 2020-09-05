import numpy as np
import unittest

from circleguard import ReplayPath, Mod, Circleguard
from tests.utils import CGTestCase, DELTA, UR_DELTA, RES, FRAMETIME_LIMIT

class TestCorrection(CGTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.r1 = ReplayPath(RES / "corrected_replay1.osr")

    def test_cheated(self):
        snaps = self.cg.snaps(self.r1)

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


class TestSteal(CGTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stolen1 = ReplayPath(RES / "stolen_replay1.osr")
        cls.stolen2 = ReplayPath(RES / "stolen_replay2.osr")
        cls.legit1 = ReplayPath(RES / "legit" / "legit-1.osr")
        cls.legit2 = ReplayPath(RES / "legit" / "legit-2.osr")
        cls.time_shifted1 = ReplayPath(RES / "stealing" / "stolen-time-shifted-1-1.osr")
        cls.time_shifted2 = ReplayPath(RES / "stealing" / "stolen-time-shifted-1-2.osr")

    @staticmethod
    def add_noise_and_positional_translation_to_replay(replay, pixel_offset, std_deviation):
        mean = [pixel_offset, pixel_offset]
        covariance_matrix = [[std_deviation, std_deviation],[std_deviation,std_deviation]]
        replay.xy = replay.xy + np.random.default_rng().multivariate_normal(mean, covariance_matrix, len(replay.xy))

    def test_cheated(self):
        # taken from http://redd.it/bvfv8j, remodded replay by same user (CielXDLP) from HDHR to FLHDHR
        sim = self.cg.similarity(self.stolen1, self.stolen2)
        self.assertLess(sim, Circleguard.SIM_LIMIT, "Cheated replays were not detected as cheated")

        r1 = self.stolen1
        r2 = self.stolen2
        (earlier, later) = Circleguard.order(r1, r2)

        self.assertAlmostEqual(sim, 2.20867, delta=DELTA, msg="Similarity is not correct")
        self.assertEqual(r1.map_id, r2.map_id, "Replay map ids did not match")
        self.assertEqual(r1.map_id, 1988753, "Replay map id was not correct")
        self.assertEqual(earlier.mods, Mod.HD + Mod.HR, "Earlier replay mods was not correct")
        self.assertEqual(later.mods, Mod.FL + Mod.HD + Mod.HR, "Later replay mods was not correct")
        self.assertEqual(earlier.replay_id, 2801164636, "Earlier replay id was not correct")
        self.assertEqual(later.replay_id, 2805164683, "Later replay id was not correct")
        self.assertEqual(r1.username, r2.username, "Replay usernames did not match")

    def test_cheated_time_shift(self):
        sim = self.cg.similarity(self.time_shifted1, self.time_shifted2, method="similarity")
        self.assertAlmostEqual(sim, 17.30254, delta=DELTA, msg="Similarity is not correct")

        # STEAL_SIM is currently *not* able to detect time shifts. If this
        # changes we want to know! :P
        self.assertGreater(sim, Circleguard.SIM_LIMIT)

        # STEAL_CORR should be able to, though.
        corr = self.cg.similarity(self.time_shifted1, self.time_shifted2, method="correlation")
        self.assertGreater(corr, Circleguard.CORR_LIMIT, "Cheated replays were not detected as cheated")
        self.assertAlmostEqual(corr, 0.99734, delta=DELTA, msg="Correlation is not correct")


    def test_legitimate(self):
        sim = self.cg.similarity(self.legit1, self.legit2)
        self.assertGreater(sim, Circleguard.SIM_LIMIT, "Legitimate replays were detected as stolen")

        r1 = self.legit1
        r2 = self.legit2
        (earlier, later) = Circleguard.order(r1, r2)

        self.assertAlmostEqual(sim, 23.13951, delta=DELTA, msg="Similarity is not correct")
        self.assertEqual(r1.map_id, r2.map_id, "Replay map ids did not match")
        self.assertEqual(r1.map_id, 722238, "Replay map id was not correct")
        self.assertEqual(earlier.mods, Mod.HD + Mod.NC, "Earlier replay mods was not correct")
        self.assertEqual(later.mods, Mod.HD + Mod.DT, "Later replay mods was not correct")
        self.assertEqual(earlier.replay_id, 2157431869, "Earlier replay id was not correct")
        self.assertEqual(later.replay_id, 2309618113, "Later replay id was not correct")
        self.assertEqual(earlier.username, "Crissinop", "Earlier username was not correct")
        self.assertEqual(later.username, "TemaZpro", "Later username was not correct")



    def test_robustness_to_translation(self):
        # copy replay to avoid any missahaps when we mutate the data
        stolen2 = ReplayPath(self.stolen2.path)
        self.cg.load(stolen2)
        TestSteal.add_noise_and_positional_translation_to_replay(stolen2, 10, 3)
        sim = self.cg.similarity(self.stolen1, stolen2, method="similarity")
        corr = self.cg.similarity(self.stolen1, stolen2, method="correlation")

        self.assertLess(sim, Circleguard.SIM_LIMIT, "Cheated replays were not detected as cheated with sim")
        self.assertGreater(corr, Circleguard.CORR_LIMIT, "Cheated replays were not detected as cheated with correlation")


class TestRelax(CGTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # TODO check `legit-12.osr` as well once ur calc notelock issues are
        # dealt with, which causes us to be ~3 ur off from the actual for it
        cls.replays = [ReplayPath(RES / "legit" / f"legit-{i}.osr") for i in range(1, 12)]
        cls.urs = [66.74, 66.56, 242.73, 115.54, 254.56, 90.88, 121.62, 163.01, 207.31, 198.79, 138.25]

    def test_cheated(self):
        for i, replay in enumerate(self.replays):
            self.assertAlmostEqual(self.cg.ur(replay), self.urs[i], delta=UR_DELTA)

class TestTimewarp(CGTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.timewarped1 = ReplayPath(RES / "timewarped" / "timewarped-1.osr")
        cls.timewarped2 = ReplayPath(RES / "timewarped" / "timewarped-2.osr")
        cls.timewarped3 = ReplayPath(RES / "timewarped" / "timewarped-3.osr")
        cls.timewarped4 = ReplayPath(RES / "timewarped" / "timewarped-4.osr")

        cls.legit = ReplayPath(RES / "legit" / "legit-1.osr")

    def test_cheated(self):
        replays = [self.timewarped1, self.timewarped2, self.timewarped3, self.timewarped4]
        for replay in replays:
            frametime = self.cg.frametime(replay)
            self.assertLess(frametime, FRAMETIME_LIMIT, f"Timewarped replay {replay} was not detected as cheated")
