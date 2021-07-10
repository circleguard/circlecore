from pathlib import Path
import logging
from tempfile import TemporaryDirectory
from typing import Iterable, Union, Tuple
import weakref

from slider import Library

from circleguard.loader import Loader
from circleguard.comparer import Comparer
from circleguard.investigator import Investigator, Judgment, Snap
from circleguard.cacher import Cacher
from circleguard.utils import convert_statistic, check_param
from circleguard.loadables import (Map, User, MapUser, ReplayMap, ReplayID,
    ReplayPath, ReplayString)
from circleguard.mod import Mod
# from circleguard.frametime_graph import FrametimeGraph


class Circleguard:
    """
    Circleguard is the main entry point for using circlecore. In particular, we
    provide methods to calculate various statistics about
    :class:`~circleguard.loadables.Replay`\s:

    * :meth:`~.similarity` - the similarity between two replays.
    * :meth:`~.ur` - the unstable rate of a replay.
    * :meth:`~.snaps` - any unusual snaps in the cursor movement of a replay.
    * :meth:`~.frametime` - the average frametime of a replay.
    * :meth:`~.frametimes` - a list of the time between frames of a replay.
    * :meth:`~.hits` - the locations in a replay where a hitobject is hit.

    We also provide methods to interact with
    :class:`~circleguard.loadables.Loadable`\s:

    * :meth:`~.load` - loads a :class:`~circleguard.loadables.Loadable`.
    * :meth:`~.load_info` - loads the info of a
      :class:`~circleguard.loadables.ReplayContainer`.
    * :meth:`~.Map` - creates a new :class:`~circleguard.loadables.Map` and
      loads its info.
    * :meth:`~.User` - creates a new :class:`~circleguard.loadables.User` and
      loads its info.
    * :meth:`~.MapUser` - creates a new :class:`~circleguard.loadables.MapUser`
      and loads its info.

    Parameters
    ----------
    key: str
        A valid api key. Can be retrieved from https://osu.ppy.sh/p/api/.
    db_path: str or :class:`os.PathLike`
        The path to the database file to read and write cached replays. If the
        path does not exist, a fresh database will be created there.
        If ``None``, no replays will be cached or loaded from cache.
    slider_dir: str or :class:`os.PathLike`
        The path to the directory used by :class:`slider.library.Library` to
        store beatmaps. If ``None``, a temporary directory will be created for
        :class:`slider.library.Library` and subsequently destroyed when this
        :class:`~Circleguard` object is garbage collected.
    loader: :class:`~circleguard.loader.Loader`
        This loader will be used instead of the base loader if passed.
        This must be the class itself, *not* an instantiation of it. It will be
        instantiated with two args - a key and a cacher.
    """
    DEFAULT_ANGLE = 10
    DEFAULT_DISTANCE = 8
    # A good balance between speed and accuracy when calculating correlation.
    DEFAULT_CHUNKS = 5

    # We provide suggested "cheated thresholds" for comparisons, as those
    # algorithms are our own invention and consumers should not be expected to
    # know how they work at anything but a high level.
    # We do not, however, provide thresholds for any other statistic, as they
    # are usually gameplay statistics that consumers should understand well
    # enough to define their own threshold.
    SIM_LIMIT = 17
    CORR_LIMIT = 0.99

    def __init__(self, key, db_path=None, slider_dir=None, loader=None, \
        cache=True):
        self._cache = cache
        self.cacher = None
        if db_path is not None:
            # resolve relative paths
            db_path = Path(db_path).absolute()
            self.cacher = Cacher(self._cache, db_path)

        self.log = logging.getLogger(__name__)

        # allow for people to pass their own loader implementation/subclass.
        # Mostly exposed for circleguard (the gui).
        LoaderClass = Loader if loader is None else loader
        self.loader = LoaderClass(key, self.cacher)

        if slider_dir:
            self.library = Library(slider_dir)
        else:
            # If slider dir wasn't passed, use a temporary library which will
            # effectively cache beatmaps for just this cg instance.
            # Have to keep a reference to this dir or the folder gets deleted.
            self.slider_dir = TemporaryDirectory()
            self.library = Library(self.slider_dir.name)
            # clean up our library (which resides in a temporary dir) or else
            # garbage collection of this cg object (and subsequently the
            # temp dir and library) will cause an error to be thrown. This
            # happens because the temp dir's finalizer is called first, which
            # tries to remove the directory, but it can't because the library's
            # sql connection to the db file in that dir is still alive, and a
            # PermissionError is thrown. We need to close the library before
            # the temp dir is finalized.
            # Errors that happen during garbage collection are ignored I
            # believe, so this only fixes the error message appearing (which is
            # still a good thing to do) rather than actually fixing any programs
            # that broke because of this.
            self._finalizer = weakref.finalize(self, self._cleanup,
                self.library)


    def similarity(self, replay1, replay2, method="similarity", \
        num_chunks=DEFAULT_CHUNKS, mods_unknown="best") -> \
        Union[float, Tuple[float]]:
        """
        The similarity between ``replay1`` and ``replay2``.

        Parameters
        ----------
        replay1: :class:`~circleguard.loadables.Replay`
            The replay to compare against ``replay2``.
        replay2: :class:`~circleguard.loadables.Replay`
            The replay to compare against ``replay1``.
        method: {"similarity", "correlation"}
            What method to use to calculate the similarity between the replays.
            |br|
            ``similarity`` is (roughly speaking) the average distance
            between the two replays in pixels. A replay compared to itself (or
            an exact copy) has a similarity of 0. See
            :data:`~circleguard.Circleguard.SIM_LIMIT` for a suggested number
            where similarities below this number indicate a stolen replay.
            |br|
            ``correlation`` is a signal-processing metric which measures how
            similar two signals (or replays, in our case) are. Correlation also
            takes into account time shifts, so a replay which is a perfect copy
            of another replay but consistently lags 10 ms behind will still have
            a perfect correltion of ``1``. The higher correlation, the more
            correlated (or similar) the two replays are. See
            :data:`~circleguard.Circleguard.CORR_LIMIT` for a suggested number
            where correlations above this number indicate a stolen replay.
        num_chunks: int
            How many chunks to split the replay into when comparing. This
            parameter only has an affect if ``method`` is ``correlation``.
            Note that runtime increases linearly with the number of chunks.
        mods_unknown: {"best", "both"}
            What to do if one or both of ``replay1`` and ``replay2`` do not
            know what mods they were played with. In this case, the similarity
            will be computed twice, both with no modifications and with
            ``Mod.HR`` applied to ``replay1``.
            |br|
            If ``best`` is passed, the best (that is, lowest if ``method`` is
            ``similarity`` and highest if ``method`` is ``correlation``)
            similarity of these two calculations is returned.
            |br|
            If ``both`` is passed, a tuple with two floats is returned. The
            first element is the similarity with no modifications, and the
            second element is the similarity with ``Mod.HR`` applied to
            ``replay1``.

        Returns
        -------
        float
            If ``method`` is ``similarity``, this is the similarity of the two
            replays. If ``method`` is ``correlation``, this is the correlation
            between the two replays.
        (float, float)
            If ``mods_unknown`` is ``both``, a tuple with two floats
            is returned. The first element is the similarity with no
            modifications, and the second element is the similarity with
            ``Mod.HR`` applied to ``replay1``. See the documentation for the
            ``mods_unknown`` parameter for more information.
        """
        check_param(method, ["similarity", "correlation"])
        check_param(mods_unknown, ["best", "both"])

        self.load(replay1)
        self.load(replay2)
        return Comparer.similarity(replay1, replay2, method, num_chunks,
            mods_unknown)


    def ur(self, replay, cv=True, beatmap=None) -> float:
        """
        The unstable rate of ``replay``.

        Parameters
        ----------
        replay: :class:`~circleguard.loadables.Replay`
            The replay to calculate the ur of.
        cv: bool
            Whether to return the converted or unconverted ur. The converted ur
            is returned by default.
        beatmap: :class:`slider.beatmap.Beatmap`
            The beatmap to use to calculate ur for the ``replay``, instead of
            retrieving a beatmap from the replay itself.
            |br|
            This parameter is provided primarily as an optimization for when you
            already have the replay's beatmap, to avoid re-retrieving it in this
            method.

        Returns
        -------
        float
            The ur of the replay.
        """
        self.load(replay)

        beatmap = beatmap or self.beatmap(replay)
        if not beatmap:
            raise ValueError("The ur of a replay that does not know what map "
                "it was set on cannot be calculated")

        ur = Investigator.ur(replay, beatmap)
        if cv:
            ur = convert_statistic(ur, replay.mods, to="cv")

        return ur


    def snaps(self, replay, max_angle=DEFAULT_ANGLE, \
        min_distance=DEFAULT_DISTANCE, only_on_hitobjs=True,
        beatmap=None) -> Iterable[Snap]:
        """
        Finds any snaps (sudden, jerky movement) in ``replay``.

        Parameters
        ----------
        replay: :class:`~circleguard.loadables.Replay`
            The replay to find snaps in.
        max_angle: float
            Consider only (a,b,c) where ``∠abc < max_angle``
        min_distance: float
            Consider only (a,b,c) where ``|ab| > min_distance`` and
            ``|bc| > min_distance``.
        only_on_hitobjs: bool
            Whether to only return snaps that occur on a hitobject.
        beatmap: :class:`slider.beatmap.Beatmap`
            The beatmap to use to calculate snaps for the ``replay``, instead of
            retrieving a beatmap from the replay itself. This is only used when
            ``only_on_hitobjs`` is true, since the beatmap is not necessary
            otherwise.
            |br|
            This parameter is provided primarily as an optimization for when you
            already have the replay's beatmap, to avoid re-retrieving it in this
            method.

        Returns
        -------
        list[Snap]
            The snaps of the replay.

        Notes
        -----
        Specifically, this function calculates the angle between each set of
        three points (a,b,c) and finds points where this angle is extremely
        acute and neither ``|ab|`` or ``|bc|`` are small.

        By default, only snaps which occur on a hitobject are returned. This is
        to reduce false positives from spinners, driver issues, or lifting the
        pen off the tablet and back on again.
        """
        self.load(replay)

        beatmap_ = None
        if only_on_hitobjs:
            beatmap_ = beatmap or self.beatmap(replay)
            if not beatmap_:
                raise ValueError("The snaps of a replay that does not know "
                    "what map it was set on cannot be filtered to include only "
                    "snaps on hit objects. If you cannot retrieve the beatmap, "
                    "you can pass ``only_on_hitobjs=False`` to avoid requiring "
                    "a beatmap.")

        return Investigator.snaps(replay, max_angle, min_distance, beatmap_)


    def frametime(self, replay, cv=True, mods_unknown="raise") -> float:
        """
        The median frametime (in ms) of ``replay``.

        Parameters
        ----------
        replay: :class:`~circleguard.loadables.Replay`
            The replay to calculate the median frametime of.
        cv: bool
            Whether to return the converted or unconverted frametime. The
            converted frametime is returned by default.
        mods_unknown: {"raise", "dt", "nm", "ht"}
            What to do if ``replay`` does not know what mods it was played with,
            and ``cv`` is ``True``.
            |br|
            If ``raise``, a ValueError will be raised.
            |br|
            If ``dt``, the frametime will be converted as if the replay was
            played with ``Mod.DT``.
            |br|
            If ``nm``, the frametime will be converted as if the replay was
            played  with ``Mod.NM`` (that is, not converted at all).
            |br|
            If ``ht``, the frametime will be converted as if the replay was
            played with ``Mod.HT``.

        Returns
        -------
        float
            The median frametime (in ms) of the replay.
        """
        check_param(mods_unknown, ["raise", "dt", "nm", "ht"])

        self.load(replay)
        frametime = Investigator.frametime(replay)
        if cv:
            if replay.mods:
                mods = replay.mods
            elif mods_unknown == "dt":
                mods = Mod.DT
            elif mods_unknown == "nm":
                mods = Mod.NM
            elif mods_unknown == "ht":
                mods = Mod.HT
            else:
                raise ValueError("The frametime of a replay that does not know "
                    "with what mods it was set with cannot be converted. Pass "
                    "a different option to frametime(..., mods_unknown=) if "
                    "you would like to provide a default mod for conversion.")
            frametime = convert_statistic(frametime, mods, to="cv")

        return frametime

    def frametimes(self, replay, cv=True, mods_unknown="raise") \
        -> Iterable[float]:
        """
        The time (in ms) between each frame in ``replay``.

        Parameters
        ----------
        replay: :class:`~circleguard.loadables.Replay`
            The replay to calculate the time between each frame of.
        cv: bool
            Whether to return the converted or unconverted frametimes. The
            converted frametimes is returned by default.
        mods_unknown: {"raise", "dt", "nm", "ht"}
            What to do if ``replay`` does not know what mods it was played with,
            and ``cv`` is ``True``.
            |br|
            If ``raise``, a ValueError will be raised.
            |br|
            If ``dt``, the frametime swill be converted as if the replay was
            played with ``Mod.DT``.
            |br|
            If ``nm``, the frametimes will be converted as if the replay was
            played  with ``Mod.NM`` (that is, not converted at all).
            |br|
            If ``ht``, the frametimes will be converted as if the replay was
            played with ``Mod.HT``.

        Returns
        -------
        [float]
            The time (in ms) between each frame of the replay.
            |br|
            The first element of this array corresponds to the time between the
            first and second frame, the second element to the time between the
            second and third frame, etc.
        """
        self.load(replay)
        frametimes = Investigator.frametimes(replay)
        if cv:
            if replay.mods:
                mods = replay.mods
            elif mods_unknown == "dt":
                mods = Mod.DT
            elif mods_unknown == "nm":
                mods = Mod.NM
            elif mods_unknown == "ht":
                mods = Mod.HT
            else:
                raise ValueError("The frametimes of a replay that does not "
                    "know with what mods it was set with cannot be converted. "
                    "Pass one of ``{\"dt\", \"nm\", \"ht\"}`` for "
                    "``mods_unknown``if you would like to provide a default "
                    "mod for conversion.")
            frametimes = convert_statistic(frametimes, mods, to="cv")
        return frametimes

    def hits(self, replay, within=None, beatmap=None) -> Iterable[Judgment]:
        """
        The locations in the replay where a hitobject is hit.

        Parameters
        ----------
        replay: :class:`~circleguard.loadables.Replay`
            The replay to calculate the hits of.
        within: float
            If passed, only the hits which are ``within`` pixels or less away
            from the edge of the hitobject which they hit will be returned.
            Otherwise, all hits are returned.
        beatmap: :class:`slider.beatmap.Beatmap`
            The beatmap to use to calculate hits for the ``replay``, instead of
            retrieving a beatmap from the replay itself.
            |br|
            This parameter is provided primarily as an optimization for when you
            already have the replay's beatmap, to avoid re-retrieving it in this
            method.

        Returns
        -------
        list[:class:`~circleguard.investigator.Judgment`]
            The hits of the replay.

        Notes
        -----
        In osu!lazer terminology, hits are equivalent to judgements, but
        without misses.
        """
        self.load(replay)

        beatmap = beatmap or self.beatmap(replay)
        if not beatmap:
            raise ValueError("The hits of a replay that does not know what map "
                "it was set on cannot be calculated.")

        hits = Investigator.hits(replay, beatmap)

        if not within:
            return hits

        hits = [hit for hit in hits if hit.within(within)]
        return hits

    def judgments(self, replay, beatmap=None) -> Iterable[Judgment]:
        """
        The locations in the replay where a hitobject is hit or missed.
        Judgments are marked as either misses, 50s, 100s, or 300s.

        Parameters
        ----------
        replay: :class:`~circleguard.loadables.Replay`
            The replay to calculate the judgments of.
        beatmap: :class:`slider.beatmap.Beatmap`
            The beatmap to use to calculate judgments for the ``replay``,
            instead of retrieving a beatmap from the replay itself.
            |br|
            This parameter is provided primarily as an optimization for when you
            already have the replay's beatmap, to avoid re-retrieving it in this
            method.

        Returns
        -------
        list[:class:`~circleguard.investigator.Judgment`]
            The judgments of the replay.
        """
        self.load(replay)

        beatmap = beatmap or self.beatmap(replay)
        if not beatmap:
            raise ValueError("The judgments of a replay that does not know "
                "what map it was set on cannot be calculated.")

        return Investigator.judgments(replay, beatmap)

    def frametime_graph(self, replay, cv=True, figure=None,
        show_expected_frametime=True):
        """
        Uses matplotlib to create a graph of the frametimes of the replay.

        Parameters
        ----------
        replay: :class:`~circleguard.loadables.Replay`
            The replay to graph the frametimes of.
        cv: bool
            Whether the frametimes should be converted before being graphed.
        figure: :class:`matplotlib.figure.Figure`
            If passed, this figure will be used instead of creating a new one
            with pyplot. Using this parameter is not recommended for normal
            usage. It is exposed to allow circleguard (the gui) to use this
            method, as matplotlib's pyqt compatability layer adds some
            complications which this works around.
        show_expected_frametime: bool
            Whether to show a vertical line where we expect the average
            frametime to be.

        Returns
        -------
        :module:`matplotlib.pyplot` or :class:`matplotlib.figure.Figure`
            Matplotlib's pyplot module for ease of use, so you can call
            :meth:`matplotlib.pyplot.show` on the return value of this function
            to display the graph.
            |br|
            If ``figure`` is passed, the return value is instead the passed
            figure after being modified by the frametime graph.
        """
        # we raise an ImportError if the consumer doesn't have matplotlib
        # installed, which is why we have to import it only when this function
        # is called.
        from circleguard.frametime_graph import FrametimeGraph
        from matplotlib import pyplot
        self.load(replay)
        frametime_graph = FrametimeGraph(replay, cv, figure,
            show_expected_frametime)
        # strictly speaking, I don't think this return is necessary -
        # ``FrametimeGraph`` modifies the passed figure on instantiation,
        # so consumers could just use the figure they passed in instead of the
        # return value here. Returning it anyway feels better though.
        return frametime_graph.figure if figure else pyplot


    def load(self, loadable):
        """
        Loads the ``loadable``.

        Parameters
        ----------
        loadable: :class:`~circleguard.loadables.Loadable`
            The loadable to load.

        Notes
        -----
        This is identical to calling ``loadable.load(cg.loader, cg.cache)``.
        """
        loadable.load(self.loader, self.cache)


    def load_info(self, replay_container):
        """
        Loads the info of the ``replay_container``.

        Parameters
        ----------
        replay_container: :class:`~circleguard.loadables.ReplayContainer`
            The replay container to load.

        Notes
        -----
        This is identical to calling
        ``replay_container.load_info(cg.loader)``.
        """
        replay_container.load_info(self.loader)

    def map_available(self, replay):
        return replay.map_available(self.library)

    def Map(self, map_id, span, mods=None, cache=None) -> Map:
        """
        Returns a new, info-loaded :class:`~circleguard.loadables.Map`.

        Notes
        -----
        This function is provided as a convenience for when you want to create a
        ``Map`` and load its info immediately. A common occurrence in using
        ``Circleguard`` is to want to instantiate a ``Map`` and immediately
        iterate over it to operate on its replays. However, this ``Map`` must
        be info loaded before it can be iterated over, so this function does
        that info loading for you.

        >>> # usage without this function (bad)
        >>> cg = Circleguard("key")
        >>> m = Map(221777, "1-2")
        >>> cg.load_info(m)
        >>> for replay in m:
        >>>     ...
        >>>
        >>> # usage with this function (good)
        >>> cg = Circleguard("key")
        >>> m = cg.Map(221777, "1-2")
        >>> for replay in m:
        >>>     ...
        """
        m = Map(map_id, span, mods, cache)
        self.load_info(m)
        return m

    def User(self, user_id, span, mods=None, cache=None, available_only=True) \
        -> User:
        """
        Returns a new, info-loaded :class:`~circleguard.loadables.User`.

        Notes
        -----
        This function is provided as a convenience for when you want to create a
        ``User`` and load its info immediately. A common occurrence in using
        ``Circleguard`` is to want to instantiate a ``User`` and immediately
        iterate over it to operate on its replays. However, this ``User`` must
        be info loaded before it can be iterated over, so this function does
        that info loading for you.

        >>> # usage without this function (bad)
        >>> cg = Circleguard("key")
        >>> u = User(124493, "1-2")
        >>> cg.load_info(u)
        >>> for replay in u:
        >>>     ...
        >>>
        >>> # usage with this function (good)
        >>> cg = Circleguard("key")
        >>> u = cg.User(124493, "1-2")
        >>> for replay in u:
        >>>     ...
        """
        u = User(user_id, span, mods, cache, available_only)
        self.load_info(u)
        return u

    def MapUser(self, map_id, user_id, span=Loader.MAX_MAP_SPAN, cache=None,
        available_only=True) -> MapUser:
        """
        Returns a new, info-loaded :class:`~circleguard.loadables.MapUser`.

        Notes
        -----
        This function is provided as a convenience for when you want to create a
        ``MapUser`` and load its info immediately. A common occurrence in using
        ``Circleguard`` is to want to instantiate a ``MapUser`` and immediately
        iterate over it to operate on its replays. However, this ``MapUser``
        must be info loaded before it can be iterated over, so this function
        does that info loading for you.

        >>> # usage without this function (bad)
        >>> cg = Circleguard("key")
        >>> mu = MapUser(124493, 129891)
        >>> cg.load_info(mu)
        >>> for replay in mu:
        >>>     ...
        >>>
        >>> # usage with this function (good)
        >>> cg = Circleguard("key")
        >>> mu = cg.MapUser(124493, 129891)
        >>> for replay in mu:
        >>>     ...
        """
        mu = MapUser(map_id, user_id, span, cache, available_only)
        self.load_info(mu)
        return mu

    def ReplayMap(self, map_id, user_id, mods=None, cache=None, info=None) \
        -> ReplayMap:
        """
        Returns a new, loaded :class:`~circleguard.loadables.ReplayMap`.

        Notes
        -----
        This function is provided as a convenience for when you want to create a
        ``ReplayMap`` and load it immediately. Loading can be an expensive
        operation which is why this does not occur by default.
        """
        r = ReplayMap(map_id, user_id, mods, cache, info)
        self.load(r)
        return r

    def ReplayPath(self, path, cache=None) -> ReplayPath:
        """
        Returns a new, loaded :class:`~circleguard.loadables.ReplayPath`.

        Notes
        -----
        This function is provided as a convenience for when you want to create a
        ``ReplayPath`` and load it immediately. Loading can be an expensive
        operation which is why this does not occur by default.
        """
        r = ReplayPath(path, cache)
        self.load(r)
        return r

    def ReplayString(self, replay_data_str, cache=None) -> ReplayString:
        """
        Returns a new, loaded :class:`~circleguard.loadables.ReplayString`.

        Notes
        -----
        This function is provided as a convenience for when you want to create a
        ``ReplayString`` and load it immediately. Loading can be an expensive
        operation which is why this does not occur by default.
        """
        r = ReplayString(replay_data_str, cache)
        self.load(r)
        return r

    def ReplayID(self, replay_id, cache=None) -> ReplayID:
        """
        Returns a new, loaded :class:`~circleguard.loadables.ReplayID`.

        Notes
        -----
        This function is provided as a convenience for when you want to create a
        ``ReplayID`` and load it immediately. Loading can be an expensive
        operation which is why this does not occur by default.
        """
        r = ReplayID(replay_id, cache)
        self.load(r)
        return r

    def beatmap(self, replay):
        self.load(replay)
        return replay.beatmap(self.library)

    @property
    def cache(self):
        return self._cache

    @cache.setter
    def cache(self, cache):
        self._cache = cache
        self.cacher.should_cache = cache

    @classmethod
    def _cleanup(cls, library):
        # see the call to this method for documentation on why this method
        # exists.
        library.close()

class KeylessCircleguard(Circleguard):
    """
    A :class:`~.Circleguard` for when you do not have access to an api key, but
    have loaded :class:`~circleguard.loadables.Loadable`\s that you want to
    perform operations on. It should go without saying that instances of this
    class cannot do anything that requires api access.

    ``KeylessCircleguard``s may also load ``ReplayPath``\s and
    ``ReplayString``\s, but some attributes of these replays will not be able to
    be accessed, as they require api access (such as user id or map id).

    Parameters
    ----------
    db_path: str or :class:`os.PathLike`
        The path to the database file to read and write cached replays. If the
        path does not exist, a fresh database will be created there.
        If `None`, no replays will be cached or loaded from cache.
    slider_dir: str or :class:`os.PathLike`
        The path to the directory used by :class:`slider.library.Library` to
        store beatmaps. If `None`, a temporary directory will be created for
        :class:`slider.library.Library` and subsequently destroyed when this
        :class:`~Circleguard` object is garbage collected.
    loader: :class:`~circleguard.loader.Loader`
        This loader will be used instead of the base loader if passed.
        This must be the class itself, *not* an instantiation of it. It will be
        instantiated with two args - a key and a cacher.
    """

    def __init__(self, db_path=None, slider_dir=None, loader=None, cache=True):
        # it's sufficient but not particularly rigorous to pass an invalid api
        # key here, and might interfere with future improvements (such as
        # checking the validity of the api key automatically on init).
        super().__init__("INVALID_KEY", db_path, slider_dir, loader, cache)
        # TODO this is a really terrible way of doing this, we have no way to
        # influence the creation of a loader in Circleguard.__init__ (related
        # to the above comment), but we need our loader to be null in this
        # class. Not sure how to make it more flexible. Getting rid of the
        # cacher-loader relationship might be a start, so we can then pass
        # entire loader instances to Circleguard instead of just a class.
        self.loader = None

def set_options(*, loglevel=None):
    """
    Set global options for circlecore.

    Parameters
    ---------
    logevel: int
        What level to log at. Circlecore follows standard python logging
        levels, with an added level of TRACE with a value of 5 (lower than
        debug, which is 10). The value passed to loglevel is passed directly to
        the setLevel function of the circleguard root logger. WARNING by
        default. For more information on log levels, see the standard python
        logging lib.
    """
    if loglevel is not None:
        logging.getLogger("circleguard").setLevel(loglevel)
