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
    0          : ["NM",       "NoMod"],
    1 << 0     : ["NF",      "NoFail"],
    1 << 1     : ["EZ",        "Easy"],
    1 << 2     : ["TD", "TouchDevice"],
    1 << 3     : ["HD",      "Hidden"],
    1 << 4     : ["HR",    "HardRock"],
    1 << 5     : ["SD", "SuddenDeath"],
    1 << 6     : ["DT",  "DoubleTime"],
    1 << 7     : ["RX",       "Relax"],
    1 << 8     : ["HT",    "HalfTime"],
    1 << 9     : ["NC",   "Nightcore"],
    1 << 10    : ["FL",  "Flashlight"],
    1 << 11    : ["AT",    "Autoplay"],
    1 << 12    : ["SO",     "SpunOut"],
    1 << 13    : ["AP",   "Autopilot"],
    1 << 14    : ["PF",     "Perfect"],
    1 << 15    : ["K4",        "Key4"],
    1 << 16    : ["K5",        "Key5"],
    1 << 17    : ["K6",        "Key6"],
    1 << 18    : ["K7",        "Key7"],
    1 << 19    : ["K8",        "Key8"],
    1 << 20    : ["FI",      "FadeIn"],
    1 << 21    : ["RD",      "Random"],
    1 << 22    : ["CN",      "Cinema"],
    1 << 23    : ["TP",      "Target"],
    1 << 24    : ["K9",        "Key9"],
    1 << 25    : ["CO",     "KeyCoop"],
    1 << 26    : ["K1",        "Key1"],
    1 << 27    : ["K3",        "Key3"],
    1 << 28    : ["K2",        "Key2"],
    1 << 29    : ["V2",     "ScoreV2"],
    1 << 30    : ["MR",      "Mirror"]

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
        str
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
        str
            The long name of this ModCombination.

        Examples
        --------
        >>> ModCombination(576).long_name()
        "Nightcore"
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
        return self.short_name()

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
        list[:class:`~.ModCombination`]
            A list of the component :class:`~.ModCombination`\s of this mod,
            ordered according to :const:`~circleguard.enums.Mod.ORDER`.
        """

        mods = [ModCombination(mod) for mod in int_to_mod.keys() if self.value & mod]
        mods = [mod for mod in Mod.ORDER if mod in mods] # order the mods by Mod.ORDER
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

    Common combinations are available as ``HDDT``, ``HDHR``, and ``HDDTHR``.

    Notes
    -----
    The nightcore mod is never set by itself. When we see plays set with ``NC``,
    we are really seeing a ``DT + NC`` play. ``NC`` by itself is ``512``, but
    what we expect to see is ``576`` (``512 + 64``; ``DT`` is ``64``). As such
    ``Mod.NC`` is defined to be the more intuitive version—``DT + NC``. We
    provide the true, technical version of the ``NC`` mod (``512``) as
    ``Mod._NC``.

    This same treatment and reasoning applies to ``Mod.PF``, which we define
    as ``PF + SD``. The technical version of PF is available as ``Mod._PF``.

    A full list of mods and their specification can be found at
    https://osu.ppy.sh/help/wiki/Game_Modifiers, or a more technical list at
    https://github.com/ppy/osu-api/wiki#mods.
    """

    NM  = NoMod        = ModCombination(0)
    NF  = NoFail       = ModCombination(1 << 0)
    EZ  = Easy         = ModCombination(1 << 1)
    TD  = TouchDevice  = ModCombination(1 << 2)
    HD  = Hidden       = ModCombination(1 << 3)
    HR  = HardRock     = ModCombination(1 << 4)
    SD  = SuddenDeath  = ModCombination(1 << 5)
    DT  = DoubleTime   = ModCombination(1 << 6)
    RX  = Relax        = ModCombination(1 << 7)
    HT  = HalfTime     = ModCombination(1 << 8)
    _NC = _Nightcore   = ModCombination(1 << 9)
    # most people will find it more useful for NC to be defined as it is ingame
    NC  = Nightcore    = _NC + DT
    FL  = Flashlight   = ModCombination(1 << 10)
    AT  = Autoplay     = ModCombination(1 << 11)
    SO  = SpunOut      = ModCombination(1 << 12)
    AP  = Autopilot    = ModCombination(1 << 13)
    _PF = _Perfect     = ModCombination(1 << 14)
    PF  = Perfect      = _PF + SD
    K4  = Key4         = ModCombination(1 << 15)
    K5  = Key5         = ModCombination(1 << 16)
    K6  = Key6         = ModCombination(1 << 17)
    K7  = Key7         = ModCombination(1 << 18)
    K8  = Key8         = ModCombination(1 << 19)
    FI  = FadeIn       = ModCombination(1 << 20)
    RD  = Random       = ModCombination(1 << 21)
    CN  = Cinema       = ModCombination(1 << 22)
    TP  = Target       = ModCombination(1 << 23)
    K9  = Key9         = ModCombination(1 << 24)
    CO  = KeyCoop      = ModCombination(1 << 25)
    K1  = Key1         = ModCombination(1 << 26)
    K3  = Key3         = ModCombination(1 << 27)
    K2  = Key2         = ModCombination(1 << 28)
    V2  = ScoreV2      = ModCombination(1 << 29)
    MR  = Mirror       = ModCombination(1 << 30)

    KM  = KeyMod       = K1+K2+K3+K4+K5+K6+K7+K8+K9+KeyCoop

    # common mod combinations
    HDDT = HD + DT
    HDHR = HD + HR
    HDDTHR = HD + DT + HR

    # how people naturally sort mods in combinations (HDDTHR, not DTHRHD)
    # sphinx uses repr() here
    # (see https://github.com/sphinx-doc/sphinx/issues/3857), so provide
    # our own, more human readable docstrings. #: denotes sphinx docstrings.
    #: [EZ, HD, HT, DT, _NC, HR, FL, NF, SD, _PF, RX, AP, SO, AT, V2, TD,
    #: FI, RD, CN ,TP, K1, K2, K3, K4, K5, K6, K7, K8, K9, CO, MR]
    ORDER = [EZ, HD, HT, DT, _NC, HR, FL, NF, SD, _PF, RX, AP, SO, AT,
             V2, TD, # we stop caring about order after this point
             FI, RD, CN ,TP, K1, K2, K3, K4, K5, K6, K7, K8, K9, CO, MR]


class Detect():
    """
    A cheat, or set of cheats, to run tests to detect.

    Parameters
    ----------
    value: int
        One (or a bitwise combination) of :data:`~.Detect.STEAL`,
        :data:`~.Detect.RELAX`, :data:`~.Detect.CORRECTION`,
        :data:`~.Detect.ALL`. What cheats to detect.
    """
    STEAL = 1 << 0
    RELAX = 1 << 1
    CORRECTION = 1 << 2
    ALL = STEAL + RELAX + CORRECTION

    def __init__(self, value):
        self.value = value

        # so we can reference them in :func:`~.__add__`
        self.steal_thresh = None
        self.clean_mode = None
        self.ur_thresh = None
        self.max_angle = None
        self.min_distance = None

    def __contains__(self, other):
        return bool(self.value & other)

    def __add__(self, other):
        ret = Detect(self.value | other.value)
        d = self if Detect.STEAL in self else other if Detect.STEAL in other else None
        if d:
            ret.steal_thresh = d.steal_thresh
            ret.clean_mode = d.clean_mode
        d = self if Detect.RELAX in self else other if Detect.RELAX in other else None
        if d:
            ret.ur_thresh = d.ur_thresh
        d = self if Detect.CORRECTION in self else other if Detect.CORRECTION in other else None
        if d:
            ret.max_angle = d.max_angle
            ret.min_distance = d.min_distance
        return ret

class StealDetect(Detect):
    """
    Defines a detection of replay stealing.

    Look at the average distance between the cursors of two replays.

    Parameters
    ----------
    steal_thresh: float
        If the average distance in pixels of two replays is smaller than
        this value, they are labeled cheated (stolen replays). Default 18.
    clean_mode: :class:`~.CleanMode`
        The options used to clean the replays before comparing them.
    """
    def __init__(self, steal_thresh=18, clean_mode=None):
        super().__init__(Detect.STEAL)

        self.steal_thresh = steal_thresh
        self.clean_mode = clean_mode if clean_mode else CleanMode(CleanMode.ALIGN + CleanMode.VALIDATE + CleanMode.SYNCHRONIZE)

class RelaxDetect(Detect):
    """
    Defines a detection of relax.

    Look at the ur of a replay.

    Parameters
    ----------
    ur_thresh: float
        If the ur of a replay is less than this value, it is labeled cheated
        (relaxed).
    """
    def __init__(self, ur_thresh=50):
        super().__init__(Detect.RELAX)
        self.ur_thresh = ur_thresh

class CorrectionDetect(Detect):
    """
    Defines a detection of aim correction.

    Look at each set of three points (a,b,c) in a replay and calculate the
    angle between them. Look at points where this angle is extremely acute
    and neither ``|ab|`` or ``|bc|`` are small.

    Parameters
    ----------
    max_angle: float
        Consider only (a,b,c) where ``∠abc < max_angle``.
    min_distance: float
        Consider only (a,b,c) where ``|ab| > min_distance`` and
        ``|ab| > min_distance``.

    Notes
    -----
    A replay is considered cheated (aim corrected) by this detect if there
    is a single datapoint that satsfies both ``max_angle`` and
    ``min_distance``.
    """
    def __init__(self, max_angle=10, min_distance=8):
        super().__init__(Detect.CORRECTION)
        self.max_angle = max_angle
        self.min_distance = min_distance

class CleanMode():
    """
    The specification of the options used to clean replays for comparison.

    Parameters
    ----------
    value: int
        One (or a bitwise combination) of :data:`~.CleanMode.VALIDATE`,
        :data:`~.CleanMode.SYNCHRONIZE`, :data:`~.CleanMode.ALIGN`, :data:`~.CleanMode.SEARCH`.
        The options used.
    search_step: int
        The time interval used when searching.
    step_limit: int
        The maximal amount of steps performed when searching.
    """

    # remove frames with an x or y coordinate out of the play area
    # (512 by 384 px)
    VALIDATE    = 1 << 0
    # find suitable nearly shared common timestamps for interpolation,
    # not recommended due to instability on time shifts.
    # Also remove breaks in one or both datasets, eg when one or both players
    # skip the intro of a song
    SYNCHRONIZE = 1 << 1
    # shift all replays so that their average coincides, minimizing the MSE
    ALIGN       = 1 << 2
    # use a local search over time to minimize the MSE. Effectively uses
    # VALIDATE and ALIGN.
    SEARCH      = 1 << 3

    # the fast preset which is effective in most cases, notably not time shifts
    FAST        = VALIDATE + ALIGN
    # the slow preset which is effective in almost all cases, including time
    # shifts
    SLOW        = SEARCH


    def __init__(self, value, search_step=16, step_limit=10):
        self.value = value
        self.search_step = search_step
        self.step_limit = step_limit

    def __contains__(self, other):
        return bool(self.value & other)

    def __add__(self, other):
        flags = self.value | other.value
        ret = CleanMode(flags)

        c = self if CleanMode.SEARCH in self else other if CleanMode.SEARCH in other else None

        if c:
            ret.search_step = c.search_step
            ret.step_limit = c.step_limit

        return ret

class RatelimitWeight(Enum):
    """
    How much it 'costs' to load a replay from the api.

    :data:`~.RatelimitWeight.NONE` if the load method of a replay makes no api
    calls.

    :data:`~.RatelimitWeight.LIGHT` if the load method of a replay makes only
    light api calls (anything but ``get_replay``).

    :data:`~.RatelimitWeight.HEAVY` if the load method of a replay makes any
    heavy api calls (``get_replay``).

    Notes
    -----
    This value currently has no effect on the program and is reserved for
    future functionality.
    """

    NONE  = "None"
    LIGHT = "Light"
    HEAVY = "Heavy"

class ResultType(Enum):
    """
    What type of cheat test to represent the results for.
    """

    STEAL = "Replay Stealing"
    REMOD = "Remodding"
    RELAX = "Relax"
    CORRECTION = "Aim Correction"
    TIMEWARP = "Timewarp"

class Key(IntFlag):
    M1 = 1
    M2 = 2
    K1 = 4
    K2 = 8
    SMOKE = 16

# TODO remove in 4.x
# @deprecated
Keys = Key
