import numpy as np

from circleguard import Circleguard, Mod, ReplayMap, ReplayPath, order
from tests.utils import DELTA, FRAMETIME_LIMIT, RES, UR_DELTA, KEY, cg


def test_snaps():
    r1 = ReplayPath(RES / "corrected_replay1.osr")
    snaps = cg.snaps(r1)

    assert len(snaps) == 14
    # beginning
    assert snaps[0].time == 5103
    assert abs(snaps[0].angle - 7.38491) < DELTA
    assert abs(snaps[0].distance - 16.69009) < DELTA
    # middle
    assert snaps[8].time == 71652
    assert abs(snaps[8].angle - 6.34890) < DELTA
    assert abs(snaps[8].distance - 27.59918) < DELTA
    # end
    assert snaps[13].time == 76502
    assert abs(snaps[13].angle - 3.04130) < DELTA
    assert abs(snaps[13].distance - 21.76919) < DELTA


def test_snaps_only_on_hitobjs():
    r = ReplayMap(221777, 39828)
    snaps = cg.snaps(r, only_on_hitobjs=False)
    assert len(snaps) == 6

    # beginning
    assert snaps[0].time == 3410
    assert abs(snaps[0].angle - 0.19259) < DELTA
    assert abs(snaps[0].distance - 44.61642) < DELTA
    # middle
    assert snaps[2].time == 19622
    assert abs(snaps[2].angle - 1.87673) < DELTA
    assert abs(snaps[2].distance - 76.04480) < DELTA
    # end
    assert snaps[5].time == 68833
    assert abs(snaps[5].angle - 4.39870) < DELTA
    assert abs(snaps[5].distance - 8.14900) < DELTA

    snaps = cg.snaps(r, only_on_hitobjs=True)
    assert len(snaps) == 2

    assert snaps[0].time == 68822
    assert abs(snaps[0].angle - 3.92694) < DELTA
    assert abs(snaps[0].distance - 8.14900) < DELTA

    assert snaps[1].time == 68833
    assert abs(snaps[1].angle - 4.39870) < DELTA
    assert abs(snaps[1].distance - 8.14900) < DELTA


def test_legit_snaps():
    r3 = ReplayPath(RES / "legit" / "legit_snaps-2.osr")
    r4 = ReplayPath(RES / "legit" / "legit_snaps-3.osr")
    snaps = cg.snaps(r3, only_on_hitobjs=False)
    filtered_snaps = cg.snaps(r3)
    assert len(snaps) == 1
    assert len(filtered_snaps) == 0

    snaps = cg.snaps(r4, only_on_hitobjs=False)
    filtered_snaps = cg.snaps(r4)
    assert len(snaps) == 3
    assert len(filtered_snaps) == 1


def test_snaps_only_on_hitobjs_accounts_for_time():
    r = ReplayMap(2769844, 448316, mods=Mod.HDHR)
    snaps = cg.snaps(r)
    assert len(snaps) == 0


def add_noise_and_positional_translation_to_replay(replay, pixel_offset, std_deviation):
    mean = [pixel_offset, pixel_offset]
    covariance_matrix = [
        [std_deviation, std_deviation],
        [std_deviation, std_deviation],
    ]
    replay.xy = replay.xy + np.random.default_rng().multivariate_normal(
        mean, covariance_matrix, len(replay.xy)
    )


def test_cheated():
    stolen1 = ReplayPath(RES / "stolen_replay1.osr")
    stolen2 = ReplayPath(RES / "stolen_replay2.osr")
    sim = cg.similarity(stolen1, stolen2)
    assert sim < Circleguard.SIM_LIMIT

    r1 = stolen1
    r2 = stolen2
    (earlier, later) = order(r1, r2)

    assert abs(sim - 2.20867) < DELTA
    assert r1.map_id == r2.map_id
    assert r1.map_id == 1988753
    assert earlier.mods == Mod.HD + Mod.HR
    assert later.mods == Mod.FL + Mod.HD + Mod.HR
    assert earlier.replay_id == 2801164636
    assert later.replay_id == 2805164683
    assert r1.username == r2.username


def test_cheated_time_shift():
    time_shifted1 = ReplayPath(RES / "stealing" / "stolen-time-shifted-1-1.osr")
    time_shifted2 = ReplayPath(RES / "stealing" / "stolen-time-shifted-1-2.osr")
    sim = cg.similarity(time_shifted1, time_shifted2, method="similarity")
    assert abs(sim - 17.30254) < DELTA

    # `similarity` is currently *not* able to detect time shifts. If this
    # changes we want to know! :P
    assert sim > Circleguard.SIM_LIMIT

    # `correlation` should be able to, though.
    corr = cg.similarity(time_shifted1, time_shifted2, method="correlation")
    assert corr > Circleguard.CORR_LIMIT
    assert abs(corr - 0.99734) < DELTA


def test_legitimate():
    legit1 = ReplayPath(RES / "legit" / "legit-1.osr")
    legit2 = ReplayPath(RES / "legit" / "legit-2.osr")
    sim = cg.similarity(legit1, legit2)
    assert sim > Circleguard.SIM_LIMIT

    r1 = legit1
    r2 = legit2
    (earlier, later) = order(r1, r2)

    assert abs(sim - 23.13951) < DELTA
    assert r1.map_id == r2.map_id
    assert r1.map_id == 722238
    assert earlier.mods == Mod.HD + Mod.NC
    assert later.mods == Mod.HD + Mod.DT
    assert earlier.replay_id == 2157431869
    assert later.replay_id == 2309618113
    assert earlier.username == "Crissinop"
    assert later.username == "TemaZpro"


def test_robustness_to_translation():
    stolen1 = ReplayPath(RES / "stolen_replay1.osr")
    stolen2 = ReplayPath(RES / "stolen_replay2.osr")
    # copy replay to avoid any missahaps when we mutate the data
    stolen2 = ReplayPath(stolen2.path)
    cg.load(stolen2)
    add_noise_and_positional_translation_to_replay(stolen2, 10, 3)
    sim = cg.similarity(stolen1, stolen2, method="similarity")
    corr = cg.similarity(stolen1, stolen2, method="correlation")

    assert sim < Circleguard.SIM_LIMIT
    assert corr > Circleguard.CORR_LIMIT


def test_ur():
    replays = [ReplayPath(RES / "legit" / f"legit-{i}.osr") for i in range(1, 12)]
    urs = [
        66.74,
        66.56,
        242.73,
        115.54,
        254.56,
        90.88,
        121.62,
        163.01,
        207.31,
        198.79,
        138.25,
    ]
    urs_adjusted = [
        66.73,
        63.03,
        170.23,
        110.76,
        182.22,
        88.63,
        92.53,
        104.43,
        132.06,
        160.68,
        104.58,
    ]
    for i, replay in enumerate(replays):
        assert abs(cg.ur(replay) - urs[i]) < UR_DELTA
        assert abs(cg.ur(replay, adjusted=True) - urs_adjusted[i]) < UR_DELTA


def test_timewarped():
    replays = [
        ReplayPath(RES / "timewarped" / "timewarped-1.osr"),
        ReplayPath(RES / "timewarped" / "timewarped-2.osr"),
        ReplayPath(RES / "timewarped" / "timewarped-3.osr"),
        ReplayPath(RES / "timewarped" / "timewarped-4.osr"),
    ]
    frametimes = [11.33333, 10.66666, 8, 8.66666]
    for i, replay in enumerate(replays):
        frametime = cg.frametime(replay)
        assert abs(frametime - frametimes[i]) < DELTA
        assert frametime < FRAMETIME_LIMIT


def test_hits():
    # don't use cache for this test, it changes xy values slightly
    cg = Circleguard(KEY, db_path=None)
    hits_replay = ReplayMap(221777, 2757689)
    hits = cg.hits(hits_replay)
    assert len(hits) == 1447

    # beginning
    assert hits[0].t == 22109
    assert hits[0].xy.tolist() == [24, 272.8889]
    assert hits[0].hitobject.t == 22110
    assert hits[0].hitobject.xy.tolist() == [22, 268]
    assert hits[0].hitobject.radius == 31.104

    # middle
    assert hits[524].t == 171421
    assert hits[524].xy.tolist() == [404, 233.7778]
    assert hits[524].hitobject.t == 171421
    assert hits[524].hitobject.xy.tolist() == [409, 227]
    assert hits[524].hitobject.radius == 31.104

    assert hits[1287].t == 336601
    assert hits[1287].xy.tolist() == [233.3333, 241.3333]
    assert hits[1287].hitobject.t == 336593
    assert hits[1287].hitobject.xy.tolist() == [243, 259]
    assert hits[1287].hitobject.radius == 31.104

    # end
    assert hits[1446].t == 385908
    assert hits[1446].xy.tolist() == [342.6667, 261.3333]
    assert hits[1446].hitobject.t == 385904
    assert hits[1446].hitobject.xy.tolist() == [340, 266]
    assert hits[1446].hitobject.radius == 31.104
