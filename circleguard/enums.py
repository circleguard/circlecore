from enum import Enum, Flag, IntFlag

from circleguard.exceptions import (UnknownAPIException, RatelimitException,
                InvalidKeyException, ReplayUnavailableException, InvalidJSONException)

# strings taken from osu api error responses
# [api response, exception class type, details to pass to an exception]
class Error(Enum):
    NO_REPLAY         = ["Replay not available.", ReplayUnavailableException, "Could not find any replay data. Skipping"]
    RATELIMITED       = ["Requesting too fast! Slow your operation, cap'n!", RatelimitException, "We were ratelimited. Waiting it out"]
    RETRIEVAL_FAILED  = ["Replay retrieval failed.", ReplayUnavailableException, "Replay retrieval failed. Skipping"]
    INVALID_KEY       = ["Please provide a valid API key.", InvalidKeyException, "Please provide a valid api key"]
    INVALID_JSON      = ["The api broke.", InvalidJSONException, "The api returned an invalid json response, retrying"]
    UNKNOWN           = ["Unknown error.", UnknownAPIException, "Unknown error when requesting a replay. Please report this "
                                                                "to the developers at https://github.com/circleguard/circlecore"]

int_to_mod = {
    0           : ["NM",         "NoMod"],
    1           : ["NF",        "NoFail"],
    2           : ["EZ",          "Easy"],
    4           : ["NV",       "NoVideo"],
    8           : ["HD",        "Hidden"],
    16          : ["HR",      "HardRock"],
    32          : ["SD",   "SuddenDeath"],
    64          : ["DT",    "DoubleTime"],
    128         : ["RL",         "Relax"],
    256         : ["HT",      "HalfTime"],
    512         : ["NC",     "Nightcore"],
    1024        : ["FL",    "Flashlight"],
    2048        : ["CN",      "Autoplay"],
    4096        : ["SO",       "SpunOut"],
    8192        : ["AP",     "Autopilot"],
    16384       : ["PF",       "Perfect"],
    32768       : ["K4",          "Key4"],
    65536       : ["K5",          "Key5"],
    131072      : ["K6",          "Key6"],
    262144      : ["K7",          "Key7"],
    524288      : ["K8",          "Key8"],
    1015808     : ["KM",        "keyMod"],
    1048576     : ["FI",        "FadeIn"],
    2097152     : ["RD",        "Random"],
    4194304     : ["LM",       "LastMod"],
    8388608     : ["TP","TargetPractice"],
    16777216    : ["K9",          "Key9"],
    33554432    : ["CO",          "Coop"],
    67108864    : ["K1",          "Key1"],
    134217728   : ["K3",          "Key3"],
    268435456   : ["K2",          "Key2"]
}

class ModCombination():
    """
    An ingame osu! mod, or combination of mods.

    Notes
    -----
    This class is not meant to be instantiated. Use :class:`~.Mod` and combine
    them as necessary instead.

    A full list of mods and their specification can be found at
    https://osu.ppy.sh/help/wiki/Game_Modifiers.
    """

    def __init__(self, value):
        self.value = value

    def short_name(self):
        """
        The acronym-ized names of the component mods.

        Returns
        -------
        str:
            The short name of this ModCombination.

        Examples
        --------
        >>> ModCombination(576).short_name()
        "NC"
        >>> ModCombination(24).short_name()
        "HDHR"

        Notes
        -----
        This is a function instead of an attribute set at initialization time
        because otherwise we couldn't refer to  :class:`~.Mod`\s as its class
        body isn't loaded while it's instantiating :class:`~.ModCombination`\s.

        Although technically mods such as NC are represented with two bits -
        DT and NC - being set, short_name removes DT and so returns "NC"
        rather than "DTNC".
        """

        if self.value in int_to_mod:
            # avoid infinite recursion with every mod decomposing into itself
            # ad infinitum
            return int_to_mod[self.value][0]
        else:
            component_mods = self.decompose(clean=True)
            return "".join(mod.short_name() for mod in component_mods)

    def long_name(self):
        """
        The spelled out names of the component mods.

        Returns
        -------
        str:
            The long name of this ModCombination.

        Examples
        --------
        >>> ModCombination(576).long_name()
        "Nightore"
        >>> ModCombination(24).long_name()
        "Hidden HardRock"

        Notes
        -----
        This is a function instead of an attribute set at initialization time
        because otherwise we couldn't refer to  :class:`~.Mod`\s as its class
        body isn't loaded while it's instantiating :class:`~.ModCombination`\s.

        Although technically mods such as NC are represented with two bits -
        DT and NC - being set, long_name removes DT and so returns "Nightcore"
        rather than "DoubleTime Nightcore".
        """

        if self.value in int_to_mod:
            return int_to_mod[self.value][1]
        else:
            component_mods = self.decompose(clean=True)
            return " ".join(mod.long_name() for mod in component_mods)

    def __eq__(self, other):
        """Compares the ``value`` of each object"""
        return self.value == other.value

    def __ne__(self, other):
        """Compares the ``value`` of each object"""
        return self.value != other.value

    def __add__(self, other):
        """Returns a Mod representing the bitwise OR of the two Mods"""
        return ModCombination(self.value | other.value)

    def __sub__(self, other):
        return ModCombination(self.value ^ other.value)

    def __hash__(self):
        return self.value

    def __repr__(self):
        return f"ModCombination(value={self.value})"

    def __str__(self):
        return self.short_name

    def __contains__(self, other):
        return bool(self.value & other.value)

    def decompose(self, clean=False):
        """
        Decomposes this mod into its base component mods, which are
        :class:`~.ModCombination`\s with a ``value`` of a power of two.

        Arguments
        ---------
        clean: bool
            If true, removes mods that we would think of as duplicate - if both
            NC and DT are component mods, remove DT. If both PF and SD are
            component mods, remove SD.

        Returns
        -------
        list: :class:`~.ModCombination`
            A list of the component :class:`~.ModCombination`\s of this mod.
        """
        mods = [ModCombination(mod) for mod in int_to_mod.keys() if self.value & mod]
        if not clean:
            return mods

        if Mod._NC in mods and Mod.DT in mods:
            mods.remove(Mod.DT)
        if Mod._PF in mods and Mod.SD in mods:
            mods.remove(Mod.SD)
        return mods

class Mod():
    """
    An ingame osu! mod.

    Notes
    -----
    A full list of mods and their specification can be found at
    https://osu.ppy.sh/help/wiki/Game_Modifiers.
    """

    NM  = NoMod          =  ModCombination(0)
    NF  = NoFail         =  ModCombination(1)
    EZ  = Easy           =  ModCombination(2)
    NV  = NoVideo        =  ModCombination(4)
    HD  = Hidden         =  ModCombination(8)
    HR  = HardRock       =  ModCombination(16)
    SD  = SuddenDeath    =  ModCombination(32)
    DT  = DoubleTime     =  ModCombination(64)
    RL  = Relax          =  ModCombination(128)
    HT  = HalfTime       =  ModCombination(256)
    _NC = _Nightcore     =  ModCombination(512)
    # most people will find it more useful for NC to be defined as it is ingame
    NC  = Nightcore      =  _NC + DT
    FL  = Flashlight     =  ModCombination(1024)
    CN  = Autoplay       =  ModCombination(2048)
    SO  = SpunOut        =  ModCombination(4096)
    AP  = Autopilot      =  ModCombination(8192)
    _PF = _Perfect       =  ModCombination(16384)
    PF  = Perfect        =  _PF + SD
    K4  = Key4           =  ModCombination(32768)
    K5  = Key5           =  ModCombination(65536)
    K6  = Key6           =  ModCombination(131072)
    K7  = Key7           =  ModCombination(262144)
    K8  = Key8           =  ModCombination(524288)
    KM  = keyMod         =  ModCombination(1015808)
    FI  = FadeIn         =  ModCombination(1048576)
    RD  = Random         =  ModCombination(2097152)
    LM  = LastMod        =  ModCombination(4194304)
    TP  = TargetPractice =  ModCombination(8388608)
    K9  = Key9           =  ModCombination(16777216)
    CO  = Coop           =  ModCombination(33554432)
    K1  = Key1           =  ModCombination(67108864)
    K3  = Key3           =  ModCombination(134217728)
    K2  = Key2           =  ModCombination(268435456)

    # common mod combinations
    HDDT = HD + DT
    HDHR = HD + HR
    HDDTHR = HD + HR + DT


class Detect(Flag):
                   # (in binary)
    STEAL = 1 << 0 # 0001
    RELAX = 1 << 1 # 0010
    REMOD = 1 << 2 # 0100

    ALL = STEAL | RELAX | REMOD
    NONE = 0

class RatelimitWeight(Enum):
    """
    How much it 'costs' to load a replay from the api. If the load method of a replay makes no api calls,
    the corresponding value is RatelimitWeight.NONE. If it makes only light api calls (anything but get_replay),
    the corresponding value is RatelimitWeight.LIGHT. If it makes any heavy api calls (get_replay), the
    corresponding value is RatelimitWeight.HEAVY.

    This value currently has no effect on the program and is reserved for possible future functionality.
    """

    NONE  = "none"
    LIGHT = "light"
    HEAVY = "heavy"

class ResultType(Enum):
    """
    What type of cheat test we are representing the results for.
    """

    STEAL = "replay stealing"
    REMOD = "remodding"
    RELAX = "relax"
    AIM_CORRECTION = "aim correction"
    TIMEWARP = "timewarp"

class Keys(IntFlag):
    M1 = 1
    M2 = 2
    K1 = 4
    K2 = 8
    SMOKE = 16
