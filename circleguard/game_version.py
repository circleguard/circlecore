class GameVersion(int):
    """
    Information about the version of osu! a
    :class:`~circleguard.loadables.Replay` was played on.

    Parameters
    ----------
    version: int
        The version of osu! to represent.

    concrete: bool
        Whether ``version`` is the actual version of osu! the replay was played
        on (in which case ``concrete`` should be ``True``), or just an
        approximation of the version of osu! the replay was played on (in which
        case ``concrete`` should be ``False``).
        |br|
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
    |br|
    We provide :func:`~circleguard.game_version.GameVersion.from_datetime` as a
    convenience for when you have a :class:`datetime.datetime` object
    representing the day an osu! version was released, and want to create a
    ``GameVersion`` from that.
    |br|
    This class subclasses ``int`` so consumers don't need to know or expect a
    special class when they access ``replay.game_version``. For instance, to
    get the numeric value of the game version, they would have to do
    ``replay.game_version.version`` as opposed to ``replay.game_version`` here.
    """
    def __new__(cls, version, concrete):
        ret = int.__new__(GameVersion, version)
        ret.concrete = concrete
        return ret

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
        :class:`~.GameVersion`
            The result of converting ``datetime`` to a ``GameVersion``.
        """
        version = int(datetime.strftime("%Y%m%d"))
        return GameVersion(version, concrete)

    def available(self):
        """
        Whether we can provide any information about the osu! version a replay
        was played on, whether that is a fully accurate version or just an
        estimate of the version.
        """
        return self != -1


class NoGameVersion(GameVersion):
    """
    Used when a :class:`~circleguard.loadables.Replay` has no information about
    its version, and cannot even estimate its version.
    """
    def __new__(cls):
        return super().__new__(NoGameVersion, -1, None)
