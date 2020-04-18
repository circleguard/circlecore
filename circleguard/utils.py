from logging import Formatter
from copy import copy

from circleguard.enums import Mod


########### LOGGING ##############

TRACE = 5

class ColoredFormatter(Formatter):
    """
    A subclass of :class:`logging.Formatter` that uses ANSI escape codes
    to color different parts of the :class:`logging.LogRecord` when printed to the
    console.

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

        message = c_record.msg # why is this msg, but we format it as %(message)s in the formatter? blame logging
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

######### UTIL METHODS ###########

def span_to_list(span):
    """
    Converts a span to the set of numbers covered by that span.

    Parameters
    ----------
    span: str
        The span of numbers to convert to a set. A number may occur more than
        once - whether explicitly or in a range - in the span, but will
        only occur once in the returned set.

    Returns
    -------
    set
        The set of numbers described by the `span`.

    Examples
    --------
    >>> span_to_list("1-3,6,2-4")
    {1, 2, 3, 4, 6}
    """
    ret = set()
    for s in span.split(","):
        if "-" in s:
            p = s.split("-")
            l = list(range(int(p[0]), int(p[1])+1))
            ret.update(l)
        else:
            ret.add(int(s))
    return ret

def convert_ur(ur, mods, *, to):
    """
    Converts an unstable rate to a converted unstable rate, depending on the
    mods the replay was played with.

    Parameters
    ----------
    ur: float
        The unconverted ur of the replay.
    mods: Mod
        The mods the replay was played with. Only ``Mod.DT`` and ``Mod.HT``
        will affect the unstable rate conversion.
    """
    if to not in ["cv", "ucv"]:
        raise ValueError(f"Expected one of cv, ucv. Got {to}")
    conversion_factor = 1

    if Mod.DT in mods:
        conversion_factor = (1 / 1.5) if to == "cv" else 1.5
    elif Mod.HT in mods:
        conversion_factor = (1 / 0.75) if to == "cv" else 0.75

    return ur * conversion_factor
