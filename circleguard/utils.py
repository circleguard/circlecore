from .exceptions import InvalidArgumentsException
from .enums import Mod

def mod_to_int(mod):
    """
    Returns the integer representation of a mod string. The mods in the string can be in any order -
    "HDDT" will be parsed the same as "DTHD".

    Args:
        String mod: The modstring to convert.

    Returns:
        The integer representation of the passed mod string.

    """

    mod_total = 0
    for acronym in [mod[i:i+2] for i in range(0, len(mod), 2)]:
        mod_total += Mod[acronym].value

    return mod_total

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