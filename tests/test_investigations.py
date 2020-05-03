import numpy as np

from circleguard import ReplayPath, Mod
from tests.utils import CGTestCase, DELTA, RES, THRESHOLD_STEAL

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
        self.assertEqual(snaps[14].time, 79052)
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

    @staticmethod
    def add_noise_and_positional_translation_to_replay(replay, pixel_offset, std_deviation):
        mean = [pixel_offset, pixel_offset]
        covariance_matrix = [[std_deviation, std_deviation],[std_deviation,std_deviation]]
        replay.xy = replay.xy + np.random.default_rng().multivariate_normal(mean, covariance_matrix, len(replay.xy))
        return replay

    def test_cheated(self):
        # taken from http://redd.it/bvfv8j, remodded replay by same user (CielXDLP) from HDHR to FLHDHR
        replays = [self.stolen1, self.stolen2]
        r = list(self.cg.steal_check(replays))
        self.assertEqual(len(r), 1, f"{len(r)} results returned instead of 1")
        r = r[0]
        self.assertTrue(r.similarity < THRESHOLD_STEAL, "Cheated replays were not detected as cheated")

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
        replays = [self.legit1, self.legit2]
        r = list(self.cg.steal_check(replays))
        self.assertEqual(len(r), 1, f"{len(r)} results returned instead of 1")
        r = r[0]
        self.assertFalse(r.similarity < THRESHOLD_STEAL, "Legitimate replays were detected as stolen")

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

    def test_num_invariance(self):
        replays = [self.stolen1, self.stolen2, self.legit1, self.legit2]

        for num in range(2, 5):
            r = list(self.cg.steal_check(replays[:num]))
            results_num = num * (num - 1) / 2 # n choose k formula with k=2
            self.assertEqual(len(r), results_num, f"{len(r)} results returned instead of {results_num}")
            r = r[0]
            self.assertTrue(r.similarity < THRESHOLD_STEAL, f"Cheated replays were not detected as cheated at num {num}")

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


    def test_robustness_to_translation(self):
        # taken from http://redd.it/bvfv8j, remodded replay by same user (CielXDLP) from HDHR to FLHDHR
        replays = [ReplayPath(RES / "stolen_replay1.osr"), ReplayPath(RES / "stolen_replay2.osr")]
        replay_2 = replays[1]
        self.cg.load(replay_2)
        TestSteal.add_noise_and_positional_translation_to_replay(replay_2, 10, 3)
        r = list(self.cg.steal_check(replays))

        self.assertEqual(len(r), 1, f"{len(r)} results returned instead of 1")
        r = r[0]
        self.assertTrue(r.similarity > 10 and r.correlation > 0.999, "Cheated replays were not detected as cheated")

        r1 = r.replay1
        r2 = r.replay2
        earlier = r.earlier_replay
        later = r.later_replay

        self.assertEqual(r1.map_id, r2.map_id, "Replay map ids did not match")
        self.assertEqual(r1.map_id, 1988753, "Replay map id was not correct")
        self.assertEqual(earlier.mods, Mod.HD + Mod.HR, "Earlier replay mods was not correct")
        self.assertEqual(later.mods, Mod.FL + Mod.HD + Mod.HR, "Later replay mods was not correct")
        self.assertEqual(earlier.replay_id, 2801164636, "Earlier replay id was not correct")
        self.assertEqual(later.replay_id, 2805164683, "Later replay id was not correct")
        self.assertEqual(r1.username, r2.username, "Replay usernames did not match")
