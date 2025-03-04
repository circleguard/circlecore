import pytest
from circleguard import Mod, fuzzy_mods


def test_mod_string_parsing():
    # one normal, one "special" (nc and pf), and one multimod mod
    assert Mod("HD") == Mod.HD
    assert Mod("NC") == Mod.NC
    assert Mod("SOHDDT") == Mod.HD + Mod.DT + Mod.SO

    with pytest.raises(ValueError):
        Mod("DTH")
    with pytest.raises(ValueError):
        Mod("DH")


def test_mod_str_list_parsing():
    assert Mod(["HD"]) == Mod.HD
    assert Mod(["NC"]) == Mod.NC
    assert Mod(["SO", "HD", "DT"]) == Mod.HD + Mod.DT + Mod.SO
    assert Mod(["SOHD", "DT"]) == Mod.HD + Mod.DT + Mod.SO
    assert Mod(["SOHDDT"]) == Mod.HD + Mod.DT + Mod.SO
    assert Mod(["HD", "SODT"]) == Mod.HD + Mod.DT + Mod.SO

    with pytest.raises(ValueError):
        Mod(["DTH"])
    with pytest.raises(ValueError):
        Mod(["DH"])
    with pytest.raises(ValueError):
        Mod(["DH", 0])


def test_equality_reflexivity():
    assert Mod("NC") == Mod("NC")


def test_mod_ordering():
    assert Mod("DTHDSO") == Mod("SOHDDT")
    assert Mod("DTHR").long_name() == Mod("HRDT").long_name()
    assert Mod("SOAPFLEZ").short_name() == Mod("EZSOFLAP").short_name()

    assert Mod("HD").short_name() == "HD"
    assert Mod("HR").long_name() == "HardRock"
    assert Mod("DTHR").long_name() == "DoubleTime HardRock"
    assert Mod("HRDT").long_name() == "DoubleTime HardRock"


def test_fuzzy_mod():
    mods = fuzzy_mods(Mod.HD, [Mod.DT, Mod.EZ])
    assert mods == [Mod.HD, Mod.HDDT, Mod.HD + Mod.EZ, Mod.HD + Mod.EZ + Mod.DT]

    mods = fuzzy_mods(Mod.HD, [Mod.DT])
    assert mods == [Mod.HD, Mod.HD + Mod.DT]

    mods = fuzzy_mods(Mod.NM, [Mod.DT, Mod.EZ])
    assert mods == [Mod.NM, Mod.DT, Mod.EZ, Mod.DT + Mod.EZ]
