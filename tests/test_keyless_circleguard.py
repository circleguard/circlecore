import pytest
from circleguard import (
    KeylessCircleguard,
    Map,
    MapUser,
    Mod,
    ReplayMap,
    ReplayPath,
    User,
)
from tests.utils import RES

kcg = KeylessCircleguard()


def test_loading_replaypath():
    r = ReplayPath(RES / "example_replay.osr")
    kcg.load(r)
    with pytest.raises(ValueError):
        r.map_id
    with pytest.raises(ValueError):
        r.user_id
    assert r.mods == Mod.HD + Mod.DT
    assert r.replay_id == 2029801532
    assert r.username == "MarthXT"
    assert r.loaded


def test_loading_other_loadables():
    r = ReplayMap(221777, 2757689)
    m = Map(221777, "1")
    u = User(12092800, "1")
    mu = MapUser(221777, 12092800, "1")
    with pytest.raises(ValueError):
        kcg.load(r)
    with pytest.raises(ValueError):
        kcg.load(m)
    with pytest.raises(ValueError):
        kcg.load_info(m)
    with pytest.raises(ValueError):
        kcg.load(u)
    with pytest.raises(ValueError):
        kcg.load_info(u)
    with pytest.raises(ValueError):
        kcg.load(mu)
    with pytest.raises(ValueError):
        kcg.load_info(mu)
