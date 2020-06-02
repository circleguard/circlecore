import numpy as np

from circleguard import ReplayPath, Mod, Detect, StealResultSim, StealResultCorr
from tests.utils import CGTestCase, DELTA, RES

class TestCorrection(CGTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.r1 = ReplayPath(RES / "corrected_replay1.osr")

    def test_cheated(self):
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
        self.assertEqual(snaps[14].time, 79053)
        self.assertAlmostEqual(snaps[14].angle, 8.77141, delta=DELTA)
        self.assertAlmostEqual(snaps[14].distance, 8.21841, delta=DELTA)


class TestSteal(CGTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stolen1 = ReplayPath(RES / "stolen_replay1.osr")
        cls.stolen2 = ReplayPath(RES / "stolen_replay2.osr")
        cls.legit1 = ReplayPath(RES / "legit_replay1.osr")
        cls.legit2 = ReplayPath(RES / "legit_replay2.osr")
        cls.time_shifted1 = ReplayPath(RES / "stealing" / "stolen-time-shifted-1.osr")
        cls.time_shifted2 = ReplayPath(RES / "stealing" / "stolen-time-shifted-2.osr")

    @staticmethod
    def add_noise_and_positional_translation_to_replay(replay, pixel_offset, std_deviation):
        mean = [pixel_offset, pixel_offset]
        covariance_matrix = [[std_deviation, std_deviation],[std_deviation,std_deviation]]
        replay.xy = replay.xy + np.random.default_rng().multivariate_normal(mean, covariance_matrix, len(replay.xy))

    def test_cheated(self):
        # taken from http://redd.it/bvfv8j, remodded replay by same user (CielXDLP) from HDHR to FLHDHR
        replays = [self.stolen1, self.stolen2]
        r = list(self.cg.steal_check(replays))
        self.assertEqual(len(r), 1, f"{len(r)} results returned instead of 1")
        r = r[0]
        self.assertLess(r.similarity, Detect.SIM_LIMIT, "Cheated replays were not detected as cheated")

        r1 = r.replay1
        r2 = r.replay2
        earlier = r.earlier_replay
        later = r.later_replay

        self.assertAlmostEqual(r.similarity, 2.20915, delta=DELTA, msg="Similarity is not correct")
        self.assertEqual(r1.map_id, r2.map_id, "Replay map ids did not match")
        self.assertEqual(r1.map_id, 1988753, "Replay map id was not correct")
        self.assertEqual(earlier.mods, Mod.HD + Mod.HR, "Earlier replay mods was not correct")
        self.assertEqual(later.mods, Mod.FL + Mod.HD + Mod.HR, "Later replay mods was not correct")
        self.assertEqual(earlier.replay_id, 2801164636, "Earlier replay id was not correct")
        self.assertEqual(later.replay_id, 2805164683, "Later replay id was not correct")
        self.assertEqual(r1.username, r2.username, "Replay usernames did not match")

    def test_cheated_time_shift(self):
        replays = [self.time_shifted1, self.time_shifted2]
        r = list(self.cg.steal_check(replays, method=Detect.STEAL_SIM))[0]
        self.assertAlmostEqual(r.similarity, 17.30112, delta=DELTA, msg="Similarity is not correct")

        # STEAL_SIM is currently *not* able to detect time shifts. If this
        # changes we want to know! :P
        self.assertGreater(r.similarity, Detect.SIM_LIMIT)

        # STEAL_CORR should be able to, though.
        r = list(self.cg.steal_check(replays, method=Detect.STEAL_CORR))[0]
        self.assertGreater(r.correlation, Detect.CORR_LIMIT, "Cheated replays were not detected as cheated")
        self.assertAlmostEqual(r.correlation, 0.99764, delta=DELTA, msg="Correlation is not correct")


    def test_legitimate(self):
        replays = [self.legit1, self.legit2]
        r = list(self.cg.steal_check(replays))
        self.assertEqual(len(r), 1, f"{len(r)} results returned instead of 1")
        r = r[0]
        self.assertGreater(r.similarity, Detect.SIM_LIMIT, "Legitimate replays were detected as stolen")

        r1 = r.replay1
        r2 = r.replay2
        earlier = r.earlier_replay
        later = r.later_replay

        self.assertAlmostEqual(r.similarity, 23.11035, delta=DELTA, msg="Similarity is not correct")
        self.assertEqual(r1.map_id, r2.map_id, "Replay map ids did not match")
        self.assertEqual(r1.map_id, 722238, "Replay map id was not correct")
        self.assertEqual(earlier.mods, Mod.HD + Mod.NC, "Earlier replay mods was not correct")
        self.assertEqual(later.mods, Mod.HD + Mod.DT, "Later replay mods was not correct")
        self.assertEqual(earlier.replay_id, 2157431869, "Earlier replay id was not correct")
        self.assertEqual(later.replay_id, 2309618113, "Later replay id was not correct")
        self.assertEqual(earlier.username, "Crissinop", "Earlier username was not correct")
        self.assertEqual(later.username, "TemaZpro", "Later username was not correct")

    def test_num_invariance(self):
        replays = [self.stolen1, self.stolen2, self.legit1, self.legit2]

        for num in range(2, 5):
            r = list(self.cg.steal_check(replays[:num]))
            results_num = num * (num - 1) / 2 # n choose k formula with k=2
            self.assertEqual(len(r), results_num, f"{len(r)} results returned instead of {results_num}")
            r = r[0]
            self.assertLess(r.similarity, Detect.SIM_LIMIT, f"Cheated replays were not detected as cheated at num {num}")

            r1 = r.replay1
            r2 = r.replay2
            earlier = r.earlier_replay
            later = r.later_replay

            self.assertAlmostEqual(r.similarity, 2.20915, delta=DELTA, msg=f"Similarity is not correct at num {num}")
            self.assertEqual(r1.map_id, r2.map_id, f"Replay map ids did not match at num {num}")
            self.assertEqual(r1.map_id, 1988753, f"r1 map id was not correct at num {num}")
            self.assertEqual(earlier.mods, Mod.HD + Mod.HR, f"Earlier replay mods was not correct at num {num}")
            self.assertEqual(later.mods, Mod.FL + Mod.HD + Mod.HR, f"Later replay mods was not correct at num {num}")
            self.assertEqual(earlier.replay_id, 2801164636, f"Earlier replay id was not correct at num {num}")
            self.assertEqual(later.replay_id, 2805164683, f"Later replay id was not correct at num {num}")
            self.assertEqual(r1.username, r2.username, f"Replay usernames did not match at num {num}")

    def test_robustness_to_translation(self):
        # copy replay to avoid any missahaps when we mutate the data
        stolen2 = ReplayPath(self.stolen2.path)
        replays = [self.stolen1, stolen2]
        self.cg.load(stolen2)
        TestSteal.add_noise_and_positional_translation_to_replay(stolen2, 10, 3)
        results = list(self.cg.steal_check(replays, method=Detect.STEAL_CORR | Detect.STEAL_SIM))

        self.assertEqual(len(results), 2, f"{len(results)} results returned instead of 2")
        for r in results:
            if isinstance(r, StealResultSim):
                self.assertLess(r.similarity, Detect.SIM_LIMIT, "Cheated replays were not detected as cheated with sim")
            if isinstance(r, StealResultCorr):
                self.assertGreater(r.correlation, Detect.CORR_LIMIT, "Cheated replays were not detected as cheated with corr")


class TestTimewarp(CGTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.timewarped1 = ReplayPath(RES / "timewarped" / "timewarped-1.osr")
        cls.timewarped2 = ReplayPath(RES / "timewarped" / "timewarped-2.osr")
        cls.timewarped3 = ReplayPath(RES / "timewarped" / "timewarped-3.osr")
        cls.timewarped4 = ReplayPath(RES / "timewarped" / "timewarped-4.osr")

        cls.legit = ReplayPath(RES / "legit_replay1.osr")

    def test_cheated(self):
        replays = [self.timewarped1, self.timewarped2, self.timewarped3, self.timewarped4]
        for r in self.cg.timewarp_check(replays):
            self.assertLess(r.frametime, Detect.FRAMETIME_LIMIT, "Timewarped replays were not detected as cheated")
