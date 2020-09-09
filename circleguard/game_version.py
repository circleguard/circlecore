from datetime import datetime
from functools import total_ordering

@total_ordering
class GameVersion():
    """
    Information about the version of osu! a
    :class:`circleguard.loadables.Replay` was played on.

    Parameters
    ----------
    version: int or :class:`datetime.datetime`
        The version

    concrete: bool
        Whether ``version`` is the actual version of osu! the replay was played
        on (in which case ``concrete`` should be ``True``), or just an
        approximation of the version of osu! the replay was played on (in which
        case ``concrete`` should be ``False``).
        <br>
        If the version is an approximation, you are not restricted to actual
        released versions of the game (for instance, osu! has no 20200908
        version of the game, only 20200831), but may use any day of any month
        of any year as your version. Circleguard will see that your version
        is just an estimate (as ``concrete`` will be ``False``), and act
        accordingly.

    Notes
    -----
    osu!'s versioning scheme uses a variation of Calender Versioning
    (https://calver.org/), which means that a release's version is the day that
    release was released. A new version pushed out on 09/08/2020 (MM/DD/YYYY),
    for instance, would have a version of 20200809 (YYYYMMDD).
    <br>
    We provide :func:`~.from_datetime` as a convenience for when you have a
    :class:`datetime.datetime` object representing the day an osu! version was
    released, and want to create a ``GameVersion`` from that.
    """
    def __init__(self, version, concrete):
        self.version = version
        self.concrete = concrete

    @staticmethod
    def from_datetime(datetime, concrete):
        """
        Provided as a convenience for converting a :class:`datetime.datetime`
        object to a ``GameVersion`` object.

        Parameters
        ----------
        datetime: :class:`datetime.datetime`
            The datetime to convert to a ``GameVersion`` object.
        concrete: bool
            Whether this version is concrete (ie, fully accurate) or not (ie,
            just an estimate of the replay's actual version).

        Returns
        -------
        :class`~.GameVersion`
            The result of converting ``datetime`` to a `GameVersion``.
        """
        version = int(datetime.strftime("%Y%m%d"))
        return GameVersion(version, concrete)

    def available(self):
        """
        Whether we can provide any information about the osu! version a replay
        was played on, whether that is a fully accurate version or just an
        estimate of the version.
        """
        return True

    def __eq__(self, other):
        return self.version == other.version

    def __lt__(self, other):
        return self.version < other.version


class NoGameVersion(GameVersion):
    """
    Used when a :class:`~circleguard.loadables.Replay` has no information about
    its version, and cannot even estimate its version.
    """
    def __init__(self):
        super().__init__(None, None)

    def available(self):
        return False
