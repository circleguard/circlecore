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
    Circleguard investigates replays for cheats.

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
        replay1: :class:`~circleguard.loadable.Replay`
            The replay to compare against ``replay2``.
        replay2: :class:`~circleguard.loadable.Replay`
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
            replays, which is (roughly speaking) the average distance between
            the two replays in pixels. A replay compared to itself (or an exact
            copy) has a similarity of 0.
            <br>
            If ``method`` is ``correlation``, this is the correlation between
            the two replays.
            # TODO explain correlation lol
        """
        self.load(replay1)
        self.load(replay2)
        return Comparer.similarity(replay1, replay2, method, num_chunks)


    def ur(self, replay, cv=True) -> float:
        """
        The unstable rate of ``replay``.

        Parameters
        ----------
        replay: :class:`~circleguard.loadable.Replay`
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
        replay: :class:`~circleguard.loadable.Replay`
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
        replay: :class:`~circleguard.loadable.Replay`
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
        replay: :class:`~circleguard.loadable.Replay`
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
        replay: :class:`~circleguard.loadable.Replay`
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

        filtered_hits = []
        hr = Mod.HR in replay.mods
        ez = Mod.EZ in replay.mods

        hitcircle_radius = circle_radius(beatmap.cs(hard_rock=hr, easy=ez))
        for hit in hits:
            hitobj_pos = hit.hitobject.position
            hitobj_xy = np.array([hitobj_pos.x, hitobj_pos.y])
            # value is negative when we're inside the hitobject, so take abs
            dist = abs(np.linalg.norm(hit.xy - hitobj_xy) - hitcircle_radius)

            if dist < within:
                filtered_hits.append(hit)

        return filtered_hits


    def load(self, loadable):
        """
        Loads the ``loadable``.

        Parameters
        ----------
        loadable: :class:`~circleguard.loadable.Loadable`
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
        replay_container: :class:`~circleguard.loadable.ReplayContainer`
            The replay container to load.

        Notes
        -----
        This is identical to calling
        ``replay_container.load_info(cg.loader)``.
        """
        replay_container.load_info(self.loader)


    def Map(self, map_id, span, mods=None, cache=None):
        m = Map(map_id, span, mods, cache)
        self.load_info(m)
        return m

    def User(self, user_id, span, mods=None, cache=None, available_only=True):
        u = User(user_id, span, mods, cache, available_only)
        self.load_info(u)
        return u

    def MapUser(self, map_id, user_id, span=Loader.MAX_MAP_SPAN, mods=None, \
        cache=None, available_only=True):
        mu = MapUser(map_id, user_id, span, cache, available_only)
        self.load_info(mu)
        return mu

    def _beatmap(self, map_id):
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
    have loaded :class:`~circleguard.loadable.Loadable`\s that you want to
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
        # TODO potentially improve this with an explicit `keyless` parameter
        # to `Circleguard` which allows for special `Loader` behavior
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
