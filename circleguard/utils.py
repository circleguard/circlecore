from logging import Formatter
from copy import copy
from enum import Enum, IntFlag
from itertools import product, chain, combinations

import numpy as np

from circleguard.mod import Mod


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
    This value currently has no effect in circlecore and is reserved for future
    functionality.
    """
    NONE  = "None"
    LIGHT = "Light"
    HEAVY = "Heavy"


class Key(IntFlag):
    M1    = 1 << 0
    M2    = 1 << 1
    K1    = 1 << 2
    K2    = 1 << 3
    SMOKE = 1 << 4


KEY_MASK = int(Key.M1) | int(Key.M2)


def convert_statistic(stat, mods, *, to):
    """
    Converts a game statistic to either its unconverted or converted form,
    depending on ``to``.

    Parameters
    ----------
    stat: float
        The statistic to convert.
    mods: Mod
        The mods the replay was played with. Only ``Mod.DT`` and ``Mod.HT``
        will affect the statistic conversion.
    to: {"cv", "ucv"}
        ``cv`` if the statistic should be converted to its converted form, and
        ``ucv`` if the statistic should be converted to its unconverted form.

    Notes
    -----
    This method is intended for any statistic that is modified from what we
    expect by ``Mod.DT`` or ``Mod.HT`` being applied (ie changing the game
    clock speed). This includes ur (unstable rate) and median frametime
    (time between frames).
    """
    check_param(to, ["cv", "ucv"])

    conversion_factor = 1

    if Mod.DT in mods:
        conversion_factor = (1 / 1.5)
    elif Mod.HT in mods:
        conversion_factor = (1 / 0.75)

    if to == "cv":
        return stat * conversion_factor
    return stat / conversion_factor


def order(replay1, replay2):
    """
    An ordered tuple of the given replays. The first element is the earlier
    replay, and the second element is the later replay.

    Parameters
    ----------
    replay1: Replay
        The first replay to order.
    replay2: Replay
        The second replay to order.

    Returns
    -------
    (Replay, Replay)
        The first element is the earlier replay, and the second element is the
        later replay.
    """
    if not replay1.timestamp or not replay2.timestamp:
        raise ValueError("Both replay1 and replay2 must provide a timestamp. "
            "Replays without a timestamp cannot be ordered.")
    # assume they're passed in order (earliest first); if not, switch them
    order = (replay1, replay2)
    if replay2.timestamp < replay1.timestamp:
        order = tuple(reversed(order))
    return order


def replay_pairs(replays, replays2=None):
    """
    A list of pairs of replays which can be compared against each other to cover
    all cases of replay stealing in ``replays`` and/or ``replays2``.

    If ``replays2`` is not passed (the default), this is a list of 2-tuples
    which are pairs of replays in ``replays``, where each replay will be paired
    with every other replay exactly once.

    If ``replays2`` is passed, this is a list of 2-tuples which are pairs of
    replays in where one replay is from ``replays``, the other is from
    ``replays2``, and every replay in ``replays`` is paired against every replay
    in ``replays2`` (but not against other replays in ``replays``).

    Returns
    -------
    Iterable[(Replay, Replay)]
        The first element is the earlier replay, and the second element is the
        later replay.

    Notes
    -----
    This is equivalent to ``itertools.combinations(replays, 2)`` if ``replays2``
    is ``None`` or the empty list, and ``itertools.product(replays, replays2)``
    otherwise.
    """
    if not replays2:
        return combinations(replays, 2)
    return product(replays, replays2)


def check_param(param, options):
    if param not in options:
        raise ValueError(f"Expected one of {','.join(options)}. Got {param}")


def fuzzy_mods(required_mod, optional_mods):
    """
    All mod combinations where each mod in ``optional_mods`` is allowed to be
    present or absent.

    If you don't want any mods to be required, pass ``Mod.NM`` as your
    ``required_mod``.

    Parameters
    ----------
    required_mod: class:`~circleguard.mod.ModCombination`
        What mod to require be present for all mods.
    optional_mods = [class:`~circleguard.mod.ModCombination`]
        What mods are allowed, but not required, to be present.

    Examples
    --------
    >>> fuzzy_mods(Mod.HD, [Mod.DT])
    [HD, HDDT]
    >>> fuzzy_mods(Mod.HD, [Mod.EZ, Mod.DT])
    [HD, HDDT, HDEZ, HDDTEZ]
    >>> fuzzy_mods(Mod.NM, [Mod.EZ, Mod.DT])
    [NM, DT, EZ, DTEZ]
    """

    all_mods = []
    for mods in powerset(optional_mods):
        final_mod = required_mod
        for mod in mods:
            final_mod = final_mod + mod
        all_mods.append(final_mod)

    return all_mods


def powerset(iterable):
    """
    The powerset of an iterable.

    Examples
    --------
    >>> powerset([1,2,3])
    [(), (1,), (2,), (3,), (1, 2), (1, 3), (2, 3), (1, 2, 3)]

    Notes
    -----
    https://stackoverflow.com/a/1482316
    """
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


def hitwindow(OD):
    """
    The number of milliseconds before and after a hitobject's time where that
    hitobject can be hit.
    """
    # stable converts OD (and CS), which are originally a float32, to a
    # double and this causes some hitwindows to be messed up when casted to
    # an int so we replicate this
    return int(150 + 50 * (5 - float(np.float32(OD))) / 5)

def hitwindows(OD):
    hitwindow_50 = hitwindow(OD)
    hitwindow_100 = (280 - 16 * OD) / 2
    hitwindow_300 = (160 - 12 * OD) / 2

    return (hitwindow_50, hitwindow_100, hitwindow_300)

def hitradius(CS):
    """
    The radius, in osu!pixels (?) of where a hitobject can be hit.
    """
    # attempting to match stable hitradius
    return np.float32(64 * ((1.0 - np.float32(0.7) * (float(np.float32(CS)) - 5) / 5)) / 2) * np.float32(1.00041)

def filter_outliers(arr, bias=1.5):
    """
    Returns ``arr` with outliers removed.

    Parameters
    ----------
    arr: list
        List of numbers to filter outliers from.
    bias: int
        Points in ``arr`` which are more than ``IQR * bias`` away from the first
        or third quartile of ``arr`` will be removed.
    """
    q3, q1 = np.percentile(arr, [75 ,25])
    iqr = q3 - q1
    lower_limit = q1 - (bias * iqr)
    upper_limit = q3 + (bias * iqr)
    return [x for x in arr if lower_limit < x < upper_limit]


TRACE = 5

class ColoredFormatter(Formatter):
    """
    A subclass of :class:`logging.Formatter` that uses ANSI escape codes
    to color different parts of the :class:`logging.LogRecord` when printed to
    the console.

    Notes
    -----
    Adapted from https://stackoverflow.com/a/46482050.
    """

    COLOR_PREFIX = '\033['
    COLOR_SUFFIX = '\033[0m'
    COLOR_MAPPING = {
        "TRACE"    : 90, # bright black
        "DEBUG"    : 94, # bright blue
        "INFO"     : 95, # bright magenta
        "WARNING"  : 31, # red
        "ERROR"    : 91, # bright red
        "CRITICAL" : 41, # white on red bg

        "NAME"     : 32, # green
        "MESSAGE"  : 93, # bright yellow
        "FILENAME" : 92, # bright green
        "LINENO"   : 91  # bright red
    }

    def __init__(self, patern):
        Formatter.__init__(self, patern)
        self.colored_log = "{prefix}{{color}}m{{msg}}{suffix}".format(
                    prefix=self.COLOR_PREFIX, suffix=self.COLOR_SUFFIX)

    def format(self, record):
        # c as in colored, not as in copy
        c_record = copy(record)

        # logging's choice of camelCase, not mine
        threadName = c_record.threadName
        color = self.COLOR_MAPPING["NAME"]
        c_threadName = self.colored_log.format(color=color, msg=threadName)

        levelname = c_record.levelname
        color = self.COLOR_MAPPING.get(levelname, 37) # default to white
        c_levelname = self.colored_log.format(color=color, msg=levelname)

        name = c_record.name
        color = self.COLOR_MAPPING["NAME"]
        c_name = self.colored_log.format(color=color, msg=name)

        message = c_record.msg
        color = self.COLOR_MAPPING["MESSAGE"]
        c_msg = self.colored_log.format(color=color, msg=message)

        filename = c_record.filename
        color = self.COLOR_MAPPING["FILENAME"]
        c_filename = self.colored_log.format(color=color, msg=filename)

        lineno = c_record.lineno
        color = self.COLOR_MAPPING["LINENO"]
        c_lineno = self.colored_log.format(color=color, msg=lineno)

        c_record.threadName = c_threadName
        c_record.levelname = c_levelname
        c_record.name = c_name
        c_record.msg = c_msg
        c_record.filename = c_filename
        c_record.lineno = c_lineno

        return Formatter.format(self, c_record)
