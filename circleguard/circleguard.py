from pathlib import Path
import logging
from tempfile import TemporaryDirectory
from typing import Iterable

from slider import Library
from slider.mod import circle_radius
import numpy as np

from circleguard.loader import Loader
from circleguard.comparer import Comparer
from circleguard.investigator import Investigator, Hit, Snap
from circleguard.cacher import Cacher
from circleguard.utils import convert_statistic
from circleguard.loadables import Map, User, MapUser
from circleguard.mod import Mod


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
    * :meth:`~.hits` - the places where a replay hits a hitobject by clicking on
      it.

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
    DEFAULT_ANGLE = 10
    DEFAULT_DISTANCE = 8
    # a healthy balance between speed and accuracy.
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


    def similarity(self, replay1, replay2, method="similarity", \
        num_chunks=DEFAULT_CHUNKS) -> float:
        """
        The similarity between ``replay1`` and ``replay2``.

        Parameters
        ----------
        replay1: :class:`~circleguard.loadables.Replay`
            The replay to compare against ``replay2``.
        replay2: :class:`~circleguard.loadables.Replay`
            The replay to compare against ``replay1``.
        method: str
            What method to use to investigate the loadables for replay
            stealing. This must be one of ``similarity`` or ``correlation``.
        num_chunks: int
            How many chunks to split the replay into when comparing. This
            parameter only has an affect if ``method`` is ``correlation``.
            Note that runtime increases linearly with the number of chunks.

        Returns
        -------
        float
            If ``method`` is ``similarity``, this is the similarity of the two
            replays. Similarity is (roughly speaking) the average distance
            between the two replays in pixels. A replay compared to itself (or
            an exact copy) has a similarity of 0. See
            :data:`~circleguard.Circleguard.SIM_LIMIT` for a suggested number
            where similarities under this number indicate a stolen replay.
            <br>
            If ``method`` is ``correlation``, this is the correlation between
            the two replays. Correlation is a signal-processing metric which
            measures how similar two signals (or replays, in our case) are.
            Correlation also takes into account time shifts, so a replay which
            is a perfect copy of another replay but consistently lags 10 ms
            behind will still have a perfect correltion of ``1``. The higher
            correlation, the more correlated (or similar) the two replays are.
            See :data:`~circleguard.Circleguard.CORR_LIMIT` for a suggested
            number where correlations above this number indicate a stolen
            replay.
        """
        self.load(replay1)
        self.load(replay2)
        return Comparer.similarity(replay1, replay2, method, num_chunks)


    def ur(self, replay, cv=True) -> float:
        """
        The unstable rate of ``replay``.

        Parameters
        ----------
        replay: :class:`~circleguard.loadables.Replay`
            The replay to calculate the ur of.
        cv: bool
            Whether to return the converted or unconverted ur. The converted ur
            is returned by default.

        Returns
        -------
        float
            The ur of the replay.
        """
        self.load(replay)
        bm = self._beatmap(replay.map_id)

        ur = Investigator.ur(replay, bm)
        if cv:
            ur = convert_statistic(ur, replay.mods, to="cv")

        return ur


    def snaps(self, replay, max_angle=DEFAULT_ANGLE, \
        min_distance=DEFAULT_DISTANCE) -> Iterable[Snap]:
        """
        Finds any snaps (sudden, jerky movement) in ``replay``.

        Parameters
        ----------
        replay: :class:`~circleguard.loadables.Replay`
            The replay to find snaps in.

        Returns
        -------
        list[Snap]
            The snaps of the replay. This list is empty if no snaps were found.
        """
        self.load(replay)
        return Investigator.snaps(replay, max_angle, min_distance)


    def frametime(self, replay, cv=True) -> float:
        """
        The median frametime (in ms) of ``replay``.

        Parameters
        ----------
        replay: :class:`~circleguard.loadables.Replay`
            The replay to calculate the median frametime of.
        cv: bool
            Whether to return the converted or unconverted frametime. The
            converted frametime is returned by default.

        Returns
        -------
        float
            The median frametime (in ms) of the replay.
        """
        self.load(replay)
        frametime = Investigator.frametime(replay)
        if cv:
            frametime = convert_statistic(frametime, replay.mods, to="cv")

        return frametime

    def frametimes(self, replay, cv=True) -> Iterable[float]:
        """
        The time (in ms) between each frame in ``replay``.

        Parameters
        ----------
        replay: :class:`~circleguard.loadables.Replay`
            The replay to calculate the time between each frame of.
        cv: bool
            Whether to return the converted or unconverted frametimes. The
            converted frametimes is returned by default.

        Returns
        -------
        [float]
            The time (in ms) between each frame of the replay. <br>
            The first element of this array corresponds to the time between the
            first and second frame, the second element to the time between the
            second and third frame, etc.
        """
        self.load(replay)
        frametimes = Investigator.frametimes(replay)
        if cv:
            frametimes = [convert_statistic(frametime, replay.mods, to="cv") \
                for frametime in frametimes]

        return frametimes


    def hits(self, replay, within=None) -> Iterable[Hit]:
        """
        The locations in the replay where a hitobject is hit.

        Parameters
        ----------
        replay: :class:`~circleguard.loadables.Replay`
            The replay to calculate the hits of.
        within: int
            If passed, only the hits which are ``within`` pixels or less away
            from the edge of the hitobject which they hit will be returned.
            Otherwise, all hits are returned.

        Returns
        -------
        [:class:`~circleguard.Investigator.Hit`]
            The hits of the replay.

        Notes
        -----
        In osu!lazer terminology, hits are equivalent to judgements, but
        without considering misses.
        """
        self.load(replay)
        beatmap = self._beatmap(replay.map_id)
        hits = Investigator.hits(replay, beatmap)

        if not within:
            return hits

        hr = Mod.HR in replay.mods
        ez = Mod.EZ in replay.mods
        hitcircle_radius = circle_radius(beatmap.cs(hard_rock=hr, easy=ez))
        filtered_hits = []

        for hit in hits:
            hitobj_pos = hit.hitobject.position
            hitobj_xy = np.array([hitobj_pos.x, hitobj_pos.y])
            dist = np.linalg.norm(hit.xy - hitobj_xy) - hitcircle_radius

            # value is negative since we're inside the hitobject, so take abs
            if abs(dist) < within:
                filtered_hits.append(hit)

        return filtered_hits


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


    def Map(self, map_id, span, mods=None, cache=None):
        """
        Instantiates a new :class:`~circleguard.loadables.Map`, loads its info,
        and returns the now info-loaded ``Map``.

        Notes
        -----
        This function is provided as a convenience for when you want to create a
        ``Map`` and load its info immediately. A common occurrence in using
        ``Circleguard`` is to want to instantiate a ``Map`` and immediately
        iterate over it to operate on its replays. However, this ``Map`` must
        be info loaded before it can be iterated over, so this function removes
        the need to explicitly call :meth:`~.load_info` on a ``Map`` before
        iterating.
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

    def User(self, user_id, span, mods=None, cache=None, available_only=True):
        """
        Instantiates a new :class:`~circleguard.loadables.User`, loads its info,
        and returns the now info-loaded ``User``.

        Notes
        -----
        This function is provided as a convenience for when you want to create a
        ``User`` and load its info immediately. A common occurrence in using
        ``Circleguard`` is to want to instantiate a ``User`` and immediately
        iterate over it to operate on its replays. However, this ``User`` must
        be info loaded before it can be iterated over, so this function removes
        the need to explicitly call :meth:`~.load_info` on a ``User`` before
        iterating.
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

    def MapUser(self, map_id, user_id, span=Loader.MAX_MAP_SPAN, mods=None, \
        cache=None, available_only=True):
        """
        Instantiates a new :class:`~circleguard.loadables.MapUser`, loads its
        info, and returns the now info-loaded ``MapUser``.

        Notes
        -----
        This function is provided as a convenience for when you want to create a
        ``MapUser`` and load its info immediately. A common occurrence in using
        ``Circleguard`` is to want to instantiate a ``MapUser`` and immediately
        iterate over it to operate on its replays. However, this ``MapUser``
        must be info loaded before it can be iterated over, so this function
        removes the need to explicitly call :meth:`~.load_info` on a ``MapUser``
        before iterating.
        >>> # usage without this function (bad)
        >>> cg = Circleguard("key")
        >>> mu = cg.MapUser(124493, 129891)
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

    def _beatmap(self, map_id):
        """
        A beatmap corresponding to ``map_id``. If our ``library`` does not
        already have this beatmap stored, it is downloaded and saved to the
        ``library``.
        """
        return self.library.lookup_by_id(map_id, download=True, save=True)

    @property
    def cache(self):
        return self._cache

    @cache.setter
    def cache(self, cache):
        self._cache = cache
        self.cacher.should_cache = cache


class KeylessCircleguard(Circleguard):
    """
    A :class:`~.Circleguard` for when you do not have access to an api key, but
    have loaded :class:`~circleguard.loadables.Loadable`\s that you want to
    perform operations on. It should go without saying that instances of this
    class cannot do anything that requires api access.

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


    def similarity(self, replay1, replay2, method="similarity", \
        num_chunks=Circleguard.DEFAULT_CHUNKS) -> float:
        if not replay1.loaded or not replay2.loaded:
            raise ValueError("replays must be loaded before use in a "
                "KeylessCircleguard")
        return super().similarity(replay1, replay2, method, num_chunks)

    def ur(self, replay, cv=True) -> float:
        if not replay.loaded:
            raise ValueError("replays must be loaded before use in a "
                "KeylessCircleguard")
        return super().ur(replay, cv)

    def snaps(self, replay, max_angle=Circleguard.DEFAULT_ANGLE, \
        min_distance=Circleguard.DEFAULT_DISTANCE) -> Iterable[Snap]:
        if not replay.loaded:
            raise ValueError("replays must be loaded before use in a "
                "KeylessCircleguard")
        return super().snaps(replay, max_angle, min_distance)

    def frametime(self, replay, cv=True) -> float:
        if not replay.loaded:
            raise ValueError("replays must be loaded before use in a "
                "KeylessCircleguard")
        return super().frametime(replay, cv)

    def hits(self, replay, within=None) -> Iterable[Hit]:
        if not replay.loaded:
            raise ValueError("replays must be loaded before use in a "
                "KeylessCircleguard")
        return super().hits(replay, within)

    def load(self, loadable):
        raise NotImplementedError("Keyless Circleguards cannot load Loadables")

    def load_info(self, replay_container):
        raise NotImplementedError("Keyless Circleguards cannot load info for "
            "ReplayContainers")

    def Map(self, map_id, span, mods=None, cache=None):
        raise NotImplementedError("KeylessCircleguards cannot create "
            "info-loaded ReplayContainers")

    def User(self, user_id, span, mods=None, cache=None, available_only=True):
        raise NotImplementedError("KeylessCircleguards cannot create "
            "info-loaded ReplayContainers")

    def MapUser(self, map_id, user_id, span=Loader.MAX_MAP_SPAN, mods=None, \
        cache=None, available_only=True):
        raise NotImplementedError("KeylessCircleguards cannot create "
            "info-loaded ReplayContainers")


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
