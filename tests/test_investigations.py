import numpy as np

from circleguard import ReplayPath, Mod, Circleguard, order, ReplayMap
from tests.utils import CGTestCase, DELTA, UR_DELTA, RES, FRAMETIME_LIMIT


class TestSnaps(CGTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.r1 = ReplayPath(RES / "corrected_replay1.osr")
        # TODO replays r2 and r5 might not have been properly named, r2 has 0
        # snaps
        cls.r2 = ReplayPath(RES / "legit" / "legit_snaps-1.osr")
        cls.r3 = ReplayPath(RES / "legit" / "legit_snaps-2.osr")
        cls.r4 = ReplayPath(RES / "legit" / "legit_snaps-3.osr")
        cls.r5 = ReplayPath(RES / "legit" / "legit_snaps-4.osr")

    def test_snaps(self):
        snaps = self.cg.snaps(self.r1)

        self.assertEqual(len(snaps), 14)
        # beginning
        self.assertEqual(snaps[0].time, 5103)
        self.assertAlmostEqual(snaps[0].angle, 7.38491, delta=DELTA)
        self.assertAlmostEqual(snaps[0].distance, 16.69009, delta=DELTA)
        # middle
        self.assertEqual(snaps[8].time, 71652)
        self.assertAlmostEqual(snaps[8].angle, 6.34890, delta=DELTA)
        self.assertAlmostEqual(snaps[8].distance, 27.59918, delta=DELTA)
        # end
        self.assertEqual(snaps[13].time, 76502)
        self.assertAlmostEqual(snaps[13].angle, 3.04130, delta=DELTA)
        self.assertAlmostEqual(snaps[13].distance, 21.76919, delta=DELTA)

    def test_snaps_only_on_hitobjs(self):
        r = ReplayMap(221777, 39828)
        snaps = self.cg.snaps(r, only_on_hitobjs=False)
        self.assertEqual(len(snaps), 6)

        # beginning
        self.assertEqual(snaps[0].time, 3410)
        self.assertAlmostEqual(snaps[0].angle, 0.19259, delta=DELTA)
        self.assertAlmostEqual(snaps[0].distance, 44.61642, delta=DELTA)
        # middle
        self.assertEqual(snaps[2].time, 19622)
        self.assertAlmostEqual(snaps[2].angle, 1.87673, delta=DELTA)
        self.assertAlmostEqual(snaps[2].distance, 76.04480, delta=DELTA)
        # end
        self.assertEqual(snaps[5].time, 68833)
        self.assertAlmostEqual(snaps[5].angle, 4.39870, delta=DELTA)
        self.assertAlmostEqual(snaps[5].distance, 8.14900, delta=DELTA)

        snaps = self.cg.snaps(r, only_on_hitobjs=True)
        self.assertEqual(len(snaps), 2)

        self.assertEqual(snaps[0].time, 68822)
        self.assertAlmostEqual(snaps[0].angle, 3.92694, delta=DELTA)
        self.assertAlmostEqual(snaps[0].distance, 8.14900, delta=DELTA)

        self.assertEqual(snaps[1].time, 68833)
        self.assertAlmostEqual(snaps[1].angle, 4.39870, delta=DELTA)
        self.assertAlmostEqual(snaps[1].distance, 8.14900, delta=DELTA)

    def test_legit_snaps(self):
        # these replays have snaps that are picked up when we don't filter for
        # those on hitobjects. Some of them also have snaps that get through
        # that filter anyway. Test mostly exists to alert us to accidental
        # changes in behavior (either good or bad changes).

        snaps = self.cg.snaps(self.r3, only_on_hitobjs=False)
        filtered_snaps = self.cg.snaps(self.r3)
        self.assertEqual(len(snaps), 1)
        self.assertEqual(len(filtered_snaps), 0)

        snaps = self.cg.snaps(self.r4, only_on_hitobjs=False)
        filtered_snaps = self.cg.snaps(self.r4)
        self.assertEqual(len(snaps), 3)
        self.assertEqual(len(filtered_snaps), 1)

    def test_snaps_only_on_hitobjs_accounts_for_time(self):
        # checking that a frame that's in the radius of the nearest hitobj,
        # but isn't within the hitobj's hitwindow and so can't hit the note,
        # is not counted as a snap.
        # This replay previously had 1 snap in it. See
        # https://github.com/circleguard/circleguard/issues/123
        r = ReplayMap(2769844, 448316, mods=Mod.HDHR)
        snaps = self.cg.snaps(r)
        self.assertEqual(len(snaps), 0)

class TestSimilarity(CGTestCase):

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
        (earlier, later) = order(r1, r2)

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

        # `similarity` is currently *not* able to detect time shifts. If this
        # changes we want to know! :P
        self.assertGreater(sim, Circleguard.SIM_LIMIT)

        # `correlation` should be able to, though.
        corr = self.cg.similarity(self.time_shifted1, self.time_shifted2, method="correlation")
        self.assertGreater(corr, Circleguard.CORR_LIMIT, "Cheated replays were not detected as cheated")
        self.assertAlmostEqual(corr, 0.99734, delta=DELTA, msg="Correlation is not correct")

    def test_legitimate(self):
        sim = self.cg.similarity(self.legit1, self.legit2)
        self.assertGreater(sim, Circleguard.SIM_LIMIT, "Legitimate replays were detected as stolen")

        r1 = self.legit1
        r2 = self.legit2
        (earlier, later) = order(r1, r2)

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
        TestSimilarity.add_noise_and_positional_translation_to_replay(stolen2, 10, 3)
        sim = self.cg.similarity(self.stolen1, stolen2, method="similarity")
        corr = self.cg.similarity(self.stolen1, stolen2, method="correlation")

        self.assertLess(sim, Circleguard.SIM_LIMIT, "Cheated replays were not detected as cheated with sim")
        self.assertGreater(corr, Circleguard.CORR_LIMIT, "Cheated replays were not detected as cheated with correlation")


class TestUR(CGTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # TODO check `legit-12.osr` as well once ur calc notelock issues are
        # dealt with, which causes us to be ~3 ur off from its actual ur
        cls.replays = [ReplayPath(RES / "legit" / f"legit-{i}.osr") for i in range(1, 12)]
        cls.urs =          [66.74, 66.56, 242.73, 115.54, 254.56, 90.88, 121.62, 163.01, 207.31, 198.79, 138.25]
        cls.urs_adjusted = [66.73, 63.03, 170.23, 110.76, 182.22, 88.63, 92.53,  104.43, 132.06, 160.68, 104.58]

    def test_ur(self):
        for i, replay in enumerate(self.replays):
            self.assertAlmostEqual(self.cg.ur(replay), self.urs[i],
                delta=UR_DELTA, msg=f"ur differs for replay {i} ({replay})")
            self.assertAlmostEqual(self.cg.ur(replay, adjusted=True),
                self.urs_adjusted[i], delta=UR_DELTA,
                msg=f"adjusted ur differs for replay {i} ({replay})")


class TestFrametime(CGTestCase):
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
        frametimes = [11.33333, 10.66666, 8, 8.66666]
        for i, replay in enumerate(replays):
            frametime = self.cg.frametime(replay)
            self.assertAlmostEqual(frametime, frametimes[i], delta=DELTA, msg=f"Frametime was wrong for replay {replay}")
            self.assertLess(frametime, FRAMETIME_LIMIT, f"Timewarped replay {replay} was not detected as cheated")

class TestHits(CGTestCase):
    @classmethod
    def setUpClass(cls):
        # don't use cache for this test, it changes xy values slightly
        super().setUpClass(use_cache=False)
        cls.replay1 = ReplayMap(221777, 2757689)

    def test_hits(self):
        hits = self.cg.hits(self.replay1)
        self.assertEqual(len(hits), 1447)

        # beginning
        self.assertEqual(hits[0].t, 22109)
        self.assertSequenceEqual(hits[0].xy.tolist(), [24, 272.8889])
        self.assertEqual(hits[0].hitobject.t, 22110)
        self.assertSequenceEqual(hits[0].hitobject.xy.tolist(), [22, 268])
        self.assertEqual(hits[0].hitobject.radius, 31.104)

        # middle
        self.assertEqual(hits[524].t, 171421)
        self.assertSequenceEqual(hits[524].xy.tolist(), [404, 233.7778])
        self.assertEqual(hits[524].hitobject.t, 171421)
        self.assertSequenceEqual(hits[524].hitobject.xy.tolist(), [409, 227])
        self.assertEqual(hits[524].hitobject.radius, 31.104)

        self.assertEqual(hits[1287].t, 336601)
        self.assertSequenceEqual(hits[1287].xy.tolist(), [233.3333, 241.3333])
        self.assertEqual(hits[1287].hitobject.t, 336593)
        self.assertSequenceEqual(hits[1287].hitobject.xy.tolist(), [243, 259])
        self.assertEqual(hits[1287].hitobject.radius, 31.104)

        # end
        self.assertEqual(hits[1446].t, 385908)
        self.assertSequenceEqual(hits[1446].xy.tolist(), [342.6667, 261.3333])
        self.assertEqual(hits[1446].hitobject.t, 385904)
        self.assertSequenceEqual(hits[1446].hitobject.xy.tolist(), [340, 266])
        self.assertEqual(hits[1446].hitobject.radius, 31.104)
