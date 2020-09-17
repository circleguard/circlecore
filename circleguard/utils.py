from logging import Formatter
from copy import copy
from enum import Enum, IntFlag

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
    This value currently has no effect on the program and is reserved for
    future functionality.
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
    elif to == "ucv":
        return stat / conversion_factor


def order(replay1, replay2):
    """
    Returns an ordered tuple of the given replays, where the first element is
    the earlier replay and the second element is the later replay.
    """
    if not replay1.timestamp or not replay2.timestamp:
        raise ValueError("Both replay1 and replay2 must provide a timestamp. "
            "Replays without a timestamp cannot be ordered.")
    # assume they're passed in order (earliest first); if not, switch them
    order = (replay1, replay2)
    if replay2.timestamp < replay1.timestamp:
        order = tuple(reversed(order))
    return order


def check_param(param, options):
    if not param in options:
        raise ValueError(f"Expected one of {','.join(options)}. Got {param}")


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
