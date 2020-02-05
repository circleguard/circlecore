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



# https://github.com/kszlim/osu-replay-parser/blob/master/osrparse/replay.py#L64
def bits(n):
    if n == 0:
        yield 0
    while n:
        b = n & (~n+1)
        yield b
        n ^= b


class Interpolation:
    """A utility class containing coordinate interpolations."""

    @staticmethod
    def linear(x1, x2, r):
        """
        Linearly interpolates coordinate tuples x1 and x2 with ratio r.

        Args:
            Float x1: The startpoint of the interpolation.
            Float x2: The endpoint of the interpolation.
            Float r: The ratio of the points to interpolate to.
        """

        return ((1 - r) * x1[0] + r * x2[0], (1 - r) * x1[1] + r * x2[1])

    @staticmethod
    def before(x1, x2, r):
        """
        Returns the startpoint of the range.

        Args:
            Float x1: The startpoint of the interpolation.
            Float x2: The endpoint of the interpolation.
            Float r: Ignored.
        """

        return x2

def interpolate(data1, data2, interpolation=Interpolation.linear, unflip=False):
    """
    Interpolates the longer of the datas to match the timestamps of the shorter.

    Args:
        List data1: A list of tuples of (t, x, y).
        List data2: A list of tuples of (t, x, y).
        Boolean unflip: Preserves input order of data1 and data2 if True.

    Returns:
        If unflip:
            The tuple (data1, data2), where one is interpolated to the other
            and said other without uninterpolatable points.
        Else:
            The tuple (clean, inter), respectively the shortest of
            the datasets without uninterpolatable points and the longest
            interpolated to the timestamps of shortest.

    """

    flipped = False

    # if the first timestamp in data2 is before the first in data1 switch
    # so data1 always has some timestamps before data2.
    if data1[0][0] > data2[0][0]:
        flipped = not flipped
        (data1, data2) = (data2, data1)

    # get the smallest index of the timestamps after the first timestamp in data2.
    i = next((i for (i, p) in enumerate(data1) if p[0] > data2[0][0]))

    # remove all earlier timestamps, if data1 is longer than data2 keep one more
    # so that the longest always starts before the shorter dataset.
    data1 = data1[i:] if len(data1) < len(data2) else data1[i - 1:]

    if len(data1) > len(data2):
        flipped = not flipped
        (data1, data2) = (data2, data1)

    # for each point in data1 interpolate the points around the timestamp in data2.
    j = 0
    inter = []
    clean = []
    for between in data1:
        # keep a clean version with only values that can be interpolated properly.
        clean.append(between)

        # move up to the last timestamp in data2 before the current timestamp.
        while j < len(data2) - 1 and data2[j][0] < between[0]:
            j += 1

        if j == len(data2) - 1:
            break

        before = data2[j]
        after = data2[j + 1]

        # calculate time differences
        # dt1 =  ---2       , data1
        # dt2 = 1-------3   , data2
        dt1 = between[0] - before[0]
        dt2 = after[0] - before[0]

        # skip trying to interpolate to this event
        # if its surrounding events are not set apart in time
        # and replace it with the event before it
        if dt2 == 0:
            inter.append((between[0], *before[1:]))
            continue

        # interpolate the coordinates in data2
        # according to the ratios of the time differences
        x_inter = interpolation(before[1:], after[1:], dt1 / dt2)

        # filter out interpolation artifacts which send outliers even further away
        if abs(x_inter[0]) > 600 or abs(x_inter[1]) > 600:
            inter.append(between)
            continue

        t_inter = between[0]

        inter.append((t_inter, *x_inter))

    if unflip and flipped:
        (clean, inter) = (inter, clean)

    return (clean, inter)

def resample(timestamped, frequency):
    """
    Resample timestamped data at the given frequency.

    Args:
        List timestamped: A list of tuples of (t, x, y).
        Float frequency: The frequency to resample data to in Hz.

    Returns
        A list of tuples of (t, x, y) with constant time interval 1 / frequency.
    """

    i = 0
    t = timestamped[0][0]
    t_max = timestamped[-1][0]

    resampled = []

    while t < t_max:
        while timestamped[i][0] < t:
            i += 1

        dt1 = t - timestamped[i - 1][0]
        dt2 = timestamped[i][0] - timestamped[i - 1][0]

        inter = Interpolation.linear(timestamped[i - 1][1:], timestamped[i][1:], dt1 / dt2)

        resampled.append((t, *inter))
        t += 1000 / frequency

    return resampled
