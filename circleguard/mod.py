import abc

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
    A full list of mods and their specification can be found at
    https://osu.ppy.sh/help/wiki/Game_Modifiers.
    """

    @abc.abstractmethod
    def __eq__(self, other):
        pass

    @abc.abstractmethod
    def __hash__(self):
        pass

    @abc.abstractmethod
    def __contains__(self, other):
        pass


class _Mod(ModCombination):
    """
    This class only exists to allow ``Mod`` to have class ``_Mod`` objects as
    class attributes, as you can't instantiate instances of your own class in a
    class definition.
    """

    def __init__(self, value):
        super().__init__()
        self.value = value

    @staticmethod
    def _parse_mod_string(mod_string):
        """
        Creates an integer representation of a mod string made up of two letter
        mod names ("HDHR", for example).

        Parameters
        ----------
        mod_string: str
            The mod string to represent as an int.

        Returns
        -------
        int
            The integer representation of the mod string.

        Raises
        ------
        ValueError
            If mod_string is empty, not of even length, or any of its 2-length
            substrings do not correspond to a _Mod in Mod.ORDER.
        """
        if mod_string == "":
            raise ValueError("Invalid mod string (cannot be empty)")
        if len(mod_string) % 2 != 0:
            raise ValueError(f"Invalid mod string {mod_string} (not of even "
                "length)")
        mod_value = 0
        for i in range(0, len(mod_string) - 1, 2):
            single_mod = mod_string[i: i + 2]
            # there better only be one Mod that has an acronym matching ours,
            # but a comp + 0 index works too
            matching_mods = [mod for mod in Mod.ORDER if \
                mod.short_name() == single_mod]
            # ``mod.ORDER`` uses ``_NC`` and ``_PF``, and we want to parse
            # eg "NC" as "DTNC"
            if Mod._NC in matching_mods:
                matching_mods.remove(Mod._NC)
                matching_mods.append(Mod.NC)
            if Mod._PF in matching_mods:
                matching_mods.remove(Mod._PF)
                matching_mods.append(Mod.PF)
            if not matching_mods:
                raise ValueError("Invalid mod string (no matching mod found "
                    f"for {single_mod})")
            mod_value += matching_mods[0].value
        return mod_value

    def short_name(self):
        """
        The acronym-ized names of the component mods.

        Returns
        -------
        str
            The short name of this mod.

        Examples
        --------
        >>> _Mod(576).short_name()
        "NC"
        >>> _Mod(24).short_name()
        "HDHR"

        Notes
        -----
        This is a function instead of an attribute set at initialization time
        because otherwise we couldn't refer to a :class:`~.Mod`\s as its class
        body isn't loaded while it's instantiating :class:`~._Mod`\s.

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
            The long name of this mod.

        Examples
        --------
        >>> _Mod(576).long_name()
        "Nightcore"
        >>> _Mod(24).long_name()
        "Hidden HardRock"

        Notes
        -----
        This is a function instead of an attribute set at initialization time
        because otherwise we couldn't refer to  :class:`~.Mod`\s as its class
        body isn't loaded while it's instantiating :class:`~._Mod`\s.

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
        if not isinstance(other, _Mod):
            return False
        return self.value == other.value

    def __add__(self, other):
        """Returns a Mod representing the bitwise OR of the two Mods"""
        return _Mod(self.value | other.value)

    def __sub__(self, other):
        return _Mod(self.value & ~other.value)

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f"_Mod(value={self.value})"

    def __str__(self):
        return self.short_name()

    def __contains__(self, other):
        return bool(self.value & other.value)

    def decompose(self, clean=False):
        """
        Decomposes this mod into its base component mods, which are
        :class:`~._Mod`\s with a ``value`` of a power of two.

        Parameters
        ----------
        clean: bool
            If true, removes mods that we would think of as duplicate - if both
            NC and DT are component mods, remove DT. If both PF and SD are
            component mods, remove SD.

        Returns
        -------
        list[:class:`~._Mod`]
            A list of the component :class:`~._Mod`\s of this mod,
            ordered according to :const:`~circleguard.mod.Mod.ORDER`.
        """

        mods = [_Mod(mod) for mod in int_to_mod.keys() if self.value & mod]
        # order the mods by Mod.ORDER
        mods = [mod for mod in Mod.ORDER if mod in mods]
        if not clean:
            return mods

        if Mod._NC in mods and Mod.DT in mods:
            mods.remove(Mod.DT)
        if Mod._PF in mods and Mod.SD in mods:
            mods.remove(Mod.SD)
        return mods


class Mod(_Mod):
    """
    An ingame osu! mod.

    Common combinations are available as ``HDDT``, ``HDHR``, and ``HDDTHR``.

    Parameters
    ----------
    value: int or str
        A representation of the desired mod. This can either be its integer
        representation such as ``64`` for ``DT`` and ``72`` (``64`` + ``8``) for
        ``HDDT``, or a string such as ``"DT"`` for ``DT`` and ``"HDDT"`` (or
        ``DTHD``) for ``HDDT``.
        |br|
        If used, the string must be composed of two-letter acronyms for mods,
        in any order.

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

    NM  = NoMod        = _Mod(0)
    NF  = NoFail       = _Mod(1 << 0)
    EZ  = Easy         = _Mod(1 << 1)
    TD  = TouchDevice  = _Mod(1 << 2)
    HD  = Hidden       = _Mod(1 << 3)
    HR  = HardRock     = _Mod(1 << 4)
    SD  = SuddenDeath  = _Mod(1 << 5)
    DT  = DoubleTime   = _Mod(1 << 6)
    RX  = Relax        = _Mod(1 << 7)
    HT  = HalfTime     = _Mod(1 << 8)
    _NC = _Nightcore   = _Mod(1 << 9)
    # most people will find it more useful for NC to be defined as it is ingame
    NC  = Nightcore    = _NC + DT
    FL  = Flashlight   = _Mod(1 << 10)
    AT  = Autoplay     = _Mod(1 << 11)
    SO  = SpunOut      = _Mod(1 << 12)
    AP  = Autopilot    = _Mod(1 << 13)
    _PF = _Perfect     = _Mod(1 << 14)
    PF  = Perfect      = _PF + SD
    K4  = Key4         = _Mod(1 << 15)
    K5  = Key5         = _Mod(1 << 16)
    K6  = Key6         = _Mod(1 << 17)
    K7  = Key7         = _Mod(1 << 18)
    K8  = Key8         = _Mod(1 << 19)
    FI  = FadeIn       = _Mod(1 << 20)
    RD  = Random       = _Mod(1 << 21)
    CN  = Cinema       = _Mod(1 << 22)
    TP  = Target       = _Mod(1 << 23)
    K9  = Key9         = _Mod(1 << 24)
    CO  = KeyCoop      = _Mod(1 << 25)
    K1  = Key1         = _Mod(1 << 26)
    K3  = Key3         = _Mod(1 << 27)
    K2  = Key2         = _Mod(1 << 28)
    V2  = ScoreV2      = _Mod(1 << 29)
    MR  = Mirror       = _Mod(1 << 30)

    KM  = KeyMod       = K1 + K2 + K3 + K4 + K5 + K6 + K7 + K8 + K9 + KeyCoop

    # common mod combinations
    HDDT = HD + DT
    HDHR = HD + HR
    HDDTHR = HD + DT + HR

    # how people naturally sort mods in combinations (HDDTHR, not DTHRHD)
    # sphinx uses repr() here
    # (see https://github.com/sphinx-doc/sphinx/issues/3857), so provide
    # our own, more human readable docstrings. #: denotes sphinx docstrings.
    #: [NM, EZ, HD, HT, DT, _NC, HR, FL, NF, SD, _PF, RX, AP, SO, AT, V2, TD,
    #: FI, RD, CN, TP, K1, K2, K3, K4, K5, K6, K7, K8, K9, CO, MR]
    ORDER = [NM, EZ, HD, HT, DT, _NC, HR, FL, NF, SD, _PF, RX, AP, SO, AT,
             V2, TD, # we stop caring about order after this point
             FI, RD, CN, TP, K1, K2, K3, K4, K5, K6, K7, K8, K9, CO, MR]

    def __init__(self, value):
        if isinstance(value, str):
            value = _Mod._parse_mod_string(value)
        super().__init__(value)
