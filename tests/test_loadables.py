from datetime import datetime, timezone
import pytest

from circleguard import (
    Map,
    MapUser,
    Mod,
    NoInfoAvailableException,
    RatelimitWeight,
    ReplayMap,
    ReplayPath,
    ReplayString,
    User,
)
from tests.utils import RES, cg


def test_loading_replaypath():
    r = ReplayPath(RES / "example_replay.osr")
    assert not r.loaded
    cg.load(r)
    assert r.mods == Mod.HD + Mod.DT
    assert r.replay_id == 2029801532
    assert r.username == "MarthXT"
    assert r.user_id == 2909663
    assert r.weight == RatelimitWeight.LIGHT
    assert r.loaded
    assert r.beatmap_hash == "c7f9bc1fea826c0f371db08bc5ebc1cc"
    assert r.replay_hash == "266bc8a5f6e9ac0557862da6760388ef"
    assert r.count_300 == 154
    assert r.count_100 == 0
    assert r.count_50 == 0
    assert r.count_geki == 23
    assert r.count_katu == 0
    assert r.count_miss == 0
    assert r.score == 1083482
    assert r.max_combo == 186
    assert r.is_perfect_combo
    assert r.life_bar_graph is None
    assert r.timestamp == datetime(2015, 12, 16, 19, 40, 39, tzinfo=timezone.utc)


def test_loading_replaymap():
    # Toy HDHR score on Pretender
    r = ReplayMap(221777, 2757689)
    assert not r.loaded
    cg.load(r)
    assert r.map_id == 221777
    assert r.user_id == 2757689
    assert r.mods == Mod.HD + Mod.HR
    assert r.replay_id == 2832574010
    assert r.weight == RatelimitWeight.HEAVY
    assert r.username == "Toy"
    assert r.loaded
    assert r.count_300 == 1449
    assert r.count_100 == 1
    assert r.count_50 == 0
    assert r.count_geki == 339
    assert r.count_katu == 1
    assert r.count_miss == 0
    assert r.score == 89927731
    assert r.max_combo == 2388
    assert r.is_perfect_combo
    assert r.timestamp == datetime(2019, 6, 19, 3, 22, 44, tzinfo=timezone.utc)


def test_no_replay_raises():
    r = ReplayMap(234378, 13947937)
    with pytest.raises(NoInfoAvailableException):
        cg.load(r)


def test_no_replay_data_raises():
    r = ReplayPath(RES / "other" / "empty_replay_data.osr")
    with pytest.raises(ValueError):
        cg.load(r)


def test_map_load():
    m = Map(221777, "3-5")
    assert len(m.all_replays()) == 0
    assert len(m[:]) == 0
    assert not m.loaded
    assert not m.info_loaded

    cg.load_info(m)
    assert not m.loaded
    assert m.info_loaded
    assert len(m.all_replays()) == 3
    assert len(m[:]) == 3

    cg.load(m)
    assert m.loaded
    assert m.info_loaded


def test_map_slice():
    m = Map(221777, "3-5")
    cg.load_info(m)
    # sanity check (map id better be what we put in)
    assert m[0].map_id == 221777
    # 4th (kirby mix)
    assert m[1].user_id == 9665206
    # 3rd, 4th, and 5th (toy, kirby mix, dolter)
    assert [r.user_id for r in m[0:3]] == [2757689, 9665206, 6920104]
    # 3rd and 5th (toy and dolter)
    assert [r.user_id for r in m[0:3:2]] == [2757689, 6920104]


def test_no_replays_does_not_raise():
    m = Map(2245774, "1-2", Mod.NC + Mod.HR + Mod.SO + Mod.TD)
    cg.load_info(m)
    assert len(m) == 0


def test_user_load():
    user = User(124493, span="1-3")
    assert len(user.all_replays()) == 0
    assert len(user[:]) == 0
    assert not user.loaded
    assert not user.info_loaded

    cg.load_info(user)
    assert not user.loaded
    assert user.info_loaded
    assert len(user.all_replays()) == 3
    assert len(user[:]) == 3

    cg.load(user)
    assert user.loaded
    assert user.info_loaded


def test_user_slice():
    user = User(124493, span="1-3")
    cg.load_info(user)
    # sanity check (user id better be what we put in)
    assert user[0].user_id == 124493
    # 2nd (FDFD)
    assert user[1].map_id == 2249059
    # 1st, 2nd, and 3rd (shinkou, FDFD, arkadia)
    assert [r.map_id for r in user[0:3]] == [3747453, 2249059, 3645144]
    # 1st and 3rd (shinkou, arkadia)
    assert [r.map_id for r in user[0:3:2]] == [3747453, 3645144]


def test_no_replays_does_not_raise_user():
    u = User(12092800, "1-2", Mod.FL + Mod.EZ)
    cg.load_info(u)
    assert len(u) == 0


def test_replay_username_loaded():
    assert cg.User(12092800, "1-10")[0].username == "tybug"


def test_map_user_load():
    mu = MapUser(795627, 6304246, span="1-2")
    assert len(mu.all_replays()) == 0
    assert len(mu[:]) == 0
    assert not mu.loaded
    assert not mu.info_loaded

    cg.load_info(mu)
    assert not mu.loaded
    assert mu.info_loaded
    assert len(mu.all_replays()) == 2
    assert len(mu[:]) == 2

    cg.load(mu)
    assert mu.loaded
    assert mu.info_loaded


def test_map_user_slice():
    mu = MapUser(795627, 6304246, span="1-2")
    cg.load_info(mu)
    # sanity checks (user and map id better be what we put in)
    assert mu[0].user_id == 6304246
    assert mu[1].user_id == 6304246
    assert mu[0].map_id == 795627
    assert mu[1].map_id == 795627
    # test slicing
    assert [r.map_id for r in mu[0:2]] == [795627, 795627]


def test_replay_string_load():
    replay_data = open(RES / "example_replay.osr", "rb").read()
    r = ReplayString(replay_data)
    cg.load(r)
    assert r.mods == Mod.HD + Mod.DT
    assert r.replay_id == 2029801532
    assert r.username == "MarthXT"
    assert r.user_id == 2909663
    assert r.weight == RatelimitWeight.LIGHT
    assert r.loaded


def test_map_from_cg():
    m = cg.Map(221777, "1-2")
    assert m.info_loaded
    assert not m.loaded
    assert len(m) == 2


def test_user_from_cg():
    u = cg.User(124493, "2, 3-4")
    assert u.info_loaded
    assert not u.loaded
    assert len(u) == 3


def test_map_user_from_cg():
    mu = cg.MapUser(795627, 6304246, "1")
    assert mu.info_loaded
    assert not mu.loaded
    assert len(mu) == 1


def test_equality_user():
    user = User(2757689, "1-2")  # toy, #1=sidetracked day, #2=View of The River Styx
    user1 = User(2757689, "1-2", cache=False)
    user2 = User(2757689, "1-2", mods=Mod.HT)
    user3 = User(2757689, "1")
    assert user == user1
    assert user != user2
    assert user != user3


def test_equality_map():
    map_ = Map(1754777, "1-4")  # sidetracked day: umbre, karthy, -duckleader-, toy
    map1 = Map(1754777, "1-4")
    map2 = Map(1754777, "1-4", mods=Mod.HD)
    map3 = Map(1754777, "1-3")
    assert map_ == map1
    assert map_ != map2
    assert map_ != map3
