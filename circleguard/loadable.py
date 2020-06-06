import abc
import logging
from pathlib import Path
import os
import sqlite3
import random

import circleparse
import numpy as np
import wtc

from circleguard.enums import RatelimitWeight
from circleguard.mod import Mod
from circleguard.utils import TRACE
from circleguard.loader import Loader
from circleguard.span import Span

class Loadable(abc.ABC):
    """
    Represents one or multiple replays, which have replay data to be loaded from
    some additional source - the osu! api, local cache, or some other location.

    Parameters
    ----------
    cache: bool
        Whether to cache the replay data once loaded.
    """
    def __init__(self, cache):
        self.loaded = False
        self.cache = cache

    @abc.abstractmethod
    def load(self, loader, cache):
        """
        Loads the information this loadable needs to become fully loaded.
        Details left to the subclass implementation.

        Parameters
        ----------
        loader: :class:`~circleguard.loader.Loader`
            The loader to load this loadable with. Although subclasses may not
            end up using a :class:`~circleguard.loader.Loader` to load
            themselves (if they don't load anything from the osu api, for
            instance), a loader is still passed regardless.
        cache: bool
            Whether to cache the replay data once loaded. This argument
            comes from a parent—either a :class:`~.LoadableContainer` or
            :class:`~circleguard.circleguard.Circleguard` itself. Should the
            loadable already have a set ``cache`` value, that should take
            precedence over the option passed in this method, but if the
            loadable has no preference then it should respect the value passed
            here.
        """
        pass

    @abc.abstractmethod
    def __eq__(self, loadable):
        pass


class LoadableContainer(Loadable):
    """
    A loadable which contains other loadables. This means that it has three
    stages - unloaded, info loaded, and loaded.

    When info loaded, the :class:`~LoadableContainer` has :class:`~Loadable`\s
    but they are unloaded.

    When loaded, the :class:`~LoadableContainer` has loaded :class:`Loadable`\s.
    """
    def __init__(self, cache):
        super().__init__(cache)
        self.info_loaded = False

    def load(self, loader, cache=None):
        """
        Loads all :class:`~circleguard.loadable.Loadable`\s contained by this
        loadable container.

        Parameters
        ----------
        loader: :class:`~circleguard.loader.Loader`
            The loader to load the :class:`~circleguard.loadable.Loadable`\s
            with.
        """
        if self.loaded:
            return
        cascade_cache = cache if self.cache is None else self.cache
        self.load_info(loader)
        for loadable in self.all_loadables():
            loadable.load(loader, cascade_cache)
        self.loaded = True

    # TODO in core 5.0.0: don't provide a default implementation of this method.
    # we currently assume that users will only use LoadableContainer for two
    # things:
    # * needs to define ``Replay`` instances on load info and does not hold any
    #   ``LoadableContainer``s. In which case you should use ReplayContainer,
    #   which has ``load_info`` as abstract
    # * does not need to define any ``Replay`` instances on load info, and holds
    #   ``LoadableContainer``s. In which case you should use ``Check`` or
    #   subclass LoadableContainer
    # But there is a third option - needing to define ``Replay`` instances on
    # load info, *and* holding ``LoadableContainer``s. In which case this
    # default does not do what we want. It's not worth it to define this method
    # here, so move this implementation to ``Check`` (or maybe even split into
    # a further two subclasses, "does not create anything new on load info" which
    # Check would inherit from, and "does create new Loadables on load info",
    # which is the third case here).
    def load_info(self, loader):
        if self.info_loaded:
            return
        for loadable in self.all_loadables():
            if isinstance(loadable, LoadableContainer):
                loadable.load_info(loader)
        self.info_loaded = True

    @abc.abstractmethod
    def all_loadables(self):
        pass

    @abc.abstractmethod
    def all_replays(self):
        """
        Returns all the :class:`~.Replay`\s in this loadable container.

        Warnings
        --------
        If you want an accurate list of :class:`~.Replay`\s in this instance,
        you must call :func:`~circleguard.circleguard.Circleguard.load` on this
        instance before :func:`~Map.all_replays`. Otherwise, this
        instance is not info loaded, and does not have a complete list of
        replays it represents.
        """
        pass

    def __getitem__(self, key):
        replays = self.all_replays()
        if isinstance(key, slice):
            return replays[key.start:key.stop:key.step]
        else:
            return replays[key]

    def __iter__(self):
        return iter(self.all_replays())


class ReplayContainer(LoadableContainer):
    """
    A LoadableContainer that only holds Replays and subclasses thereof.

    ReplayContainer's start unloaded and become info loaded when
    :meth:`~LoadableContainer.load_info` is called. They become fully
    loaded when :meth:`~Loadable.load`
    is called (and if this is called when the ReplayContainer is in the
    unloaded state, :meth:`~Loadable.load` will load info first,
    then load the replays.)

    In the unloaded state, the container has no actual Replay objects. It may
    have limited knowledge about their number or type.

    In the info loaded state, the container has references to Replay objects,
    but those Replay objects are unloaded.

    In the loaded state, the Replay objects are loaded.
    """
    def __init__(self, cache):
        super().__init__(cache)

    # redefine as abstract. The LoadableContainer definition serves as a good
    # default implementation for other user-defined loadable containers, but not
    # for ReplayContainers and user-defined subclasses thereof.
    @abc.abstractmethod
    def load_info(self, loader):
        pass

    def all_loadables(self):
        # ReplayContainers only contain replays, so these two functions
        # are equivalent
        return self.all_replays()


class Check(LoadableContainer):
    """
    Organizes :class:`~.Loadable`\s and what to investigate them for.

    Parameters
    ----------
    loadables: list[:class:`~.Loadable`]
        The loadables to hold for investigation.
    cache: bool
        Whether to cache the loadables once they are loaded. This will be
        overriden by a ``cache`` option set by a :class:`~Loadable` in
        ``loadables``. It only affects children loadables when they do not have
        a ``cache`` option set.
    loadables2: list[:class:`~.Loadable`]
        A second set of loadables to hold. Useful for partitioning loadables for
        a replay stealing investigations.
    """

    def __init__(self, loadables, cache, loadables2=None):
        super().__init__(cache)
        self.log = logging.getLogger(__name__ + ".Check")
        self.loadables1 = [loadables] if isinstance(loadables, Loadable) else loadables
        self.loadables2 = [loadables2] if isinstance(loadables2, Loadable) else [] if loadables2 is None else loadables2

    def all_loadables(self):
        """
        Returns all the :class:`~circleguard.loadable.Loadable`\s contained by
        this check.

        Returns
        -------
        list[:class:`~Loadable`]
            All the loadables in this check.

        See Also
        --------
        :func:`~Check.all_replays`.

        Notes
        -----
        :class:`~circleguard.loadable.Loadable`\s are very different from
        :class:`~circleguard.loadable.Replay`\s -
        ``len(check.all_loadables())`` will *not* return the number of
        replays in the check, for instance.
        """
        return self.loadables1 + self.loadables2

    def all_replays(self):
        """
        Returns all the :class:`~.Replay`\s in this check. Contrast with
        :func:`~Check.all_loadables`, which returns all the
        :class:`~.Loadable`\s in this check.

        Returns
        -------
        list[:class:`~Replay`]
            All the replays in this check.
        """
        return self.all_replays1() + self.all_replays2()

    def all_replays1(self):
        """
        Returns all the :class:`~.Replay`\s contained by ``loadables1`` of this
        check.

        Returns
        -------
        list[:class:`~Replay`]
            All the replays contained by ``loadables1`` of this check.
        """
        replays = []
        for loadable in self.loadables1:
            if isinstance(loadable, LoadableContainer):
                replays += loadable.all_replays()
            else:
                replays.append(loadable) # loadable is a Replay
        return replays

    def all_replays2(self):
        """
        Returns all the :class:`~.Replay`\s contained by ``loadables2`` of this
        check.

        Returns
        -------
        list[:class:`~Replay`]
            All the replays contained by ``loadables2`` of this check.
        """
        replays2 = []
        for loadable in self.loadables2:
            if isinstance(loadable, LoadableContainer):
                replays2 += loadable.all_replays()
            else:
                replays2.append(loadable) # loadable is a Replay
        return replays2

    def __eq__(self, loadable):
        if not isinstance(loadable, Check):
            return False
        return self.all_replays() == loadable.all_replays()

    def __repr__(self):
        return (f"Check(loadables={self.loadables1},loadables2={self.loadables2},"
                f"loaded={self.loaded})")


class Map(ReplayContainer):
    """
    A map's top plays (leaderboard), as seen on the website.

    Parameters
    ----------
    map_id: int
        The map to represent the top plays for.
    span: str or Span
        A comma separated list of ranges of top plays to retrieve.
        ``span="1-3,6,2-4"`` -> replays in the range ``[1,2,3,4,6]``.
    mods: :class:`~.enums.ModCombination`
        If passed, only represent replays played with this exact mod
        combination. Due to limitations with the api, fuzzy matching is not
        implemented. <br>
        This is applied before span``. That is, if ``span="1-2"``
        and ``mods=Mod.HD``, the top two ``HD`` plays on the map are
        represented.
    cache: bool
        Whether to cache the replays once they are loaded.
    """
    def __init__(self, map_id, span, mods=None, cache=None):
        super().__init__(cache)
        self.replays = []
        self.map_id = map_id
        self.mods = mods
        self.span = Span(span)

    def load_info(self, loader):
        if self.info_loaded:
            return
        for info in loader.replay_info(self.map_id, self.span, mods=self.mods):
            self.replays.append(ReplayMap(info.map_id, info.user_id, info.mods, cache=self.cache, info=info))
        self.info_loaded = True

    def all_replays(self):
        return self.replays

    def __eq__(self, loadable):
        if not isinstance(loadable, Map):
            return False
        return (self.map_id == loadable.map_id and self.mods == loadable.mods
                and self.span == loadable.span)

    def __repr__(self):
        return (f"Map(map_id={self.map_id},cache={self.cache},mods={self.mods},"
                f"span={self.span},replays={self.replays},loaded={self.loaded})")

    def __str__(self):
        return f"Map {self.map_id}"


class User(ReplayContainer):
    """
    A user's top plays (pp-wise, as seen on the website).

    Parameters
    ----------
    user_id: int
        The user to represent the top plays for.
    span: str or Span
        A comma separated list of ranges of top plays to retrieve.
        ``span="1-3,6,2-4"`` -> replays in the range ``[1,2,3,4,6]``.
    mods: :class:`~.enums.ModCombination`
        If passed, only represent replays played with this exact mod
        combination. Due to limitations with the api, fuzzy matching is not
        implemented. <br>
        This is applied before ``span``. That is, if ``span="1-2"``
        and ``mods=Mod.HD``, the user's top two ``HD`` plays are represented.
    cache: bool
        Whether to cache the replays once they are loaded.
    available_only: bool
        Whether to represent only replays that have replay data available.
        Replays are filtered on this basis after ``mods`` and ``span``
        are applied. True by default.
    """
    def __init__(self, user_id, span, mods=None, cache=None, available_only=True):
        super().__init__(cache)
        self.replays = []
        self.user_id = user_id
        self.span = Span(span)
        self.mods = mods
        self.available_only = available_only

    def load_info(self, loader):
        if self.info_loaded:
            return
        for info in loader.get_user_best(self.user_id, span=self.span, mods=self.mods):
            if self.available_only and not info.replay_available:
                continue
            self.replays.append(ReplayMap(info.map_id, info.user_id, info.mods, cache=self.cache, info=info))
        self.info_loaded = True

    def all_replays(self):
        return self.replays

    def __eq__(self, loadable):
        if not isinstance(loadable, User):
            return False
        return (self.user_id == loadable.user_id and self.mods == loadable.mods
                and self.span == loadable.span)


class MapUser(ReplayContainer):
    """
    All replays on a map by a user, not just the top replay.

    Parameters
    ----------
    map_id: int
        The map to represent scores by `user_id` on.
    user_id: int
        The user to represent scores on `map_id` for.
    span: str or Span
        A comma separated list of ranges of plays to retrieve.
        ``span="1-3,6,2-4"`` -> replays in the range ``[1,2,3,4,6]``.
    cache: bool
        Whether to cache the replays once they are loaded.
    available_only: bool
        Whether to represent only replays that have replay data available.
        Replays are filtered on this basis after ``span`` is applied.
        True by default.
    """
    def __init__(self, map_id, user_id, span=Loader.MAX_MAP_SPAN, cache=None, available_only=True):
        super().__init__(cache)
        self.replays = []
        self.map_id = map_id
        self.user_id = user_id
        self.span = Span(span)
        self.available_only = available_only

    def load_info(self, loader):
        if self.info_loaded:
            return
        for info in loader.replay_info(self.map_id, span=self.span, user_id=self.user_id, limit=False):
            if self.available_only and not info.replay_available:
                continue
            self.replays.append(ReplayMap(info.map_id, info.user_id, info.mods, cache=self.cache, info=info))
        self.info_loaded = True

    def all_replays(self):
        return self.replays

    def __eq__(self, loadable):
        if not isinstance(loadable, MapUser):
            return False
        return (self.map_id == loadable.map_id and self.user_id == loadable.user_id
                and self.span == loadable.span)


class ReplayCache(ReplayContainer):
    """
    Contains replays represented by a circlecore database. Primarily useful
    to randomly sample these replays, rather than directly access them.

    Parameters
    ----------
    path: string
        The path to the database to load replays from.
    num_maps: int
        How many (randomly chosen) maps to load replays from.
    limit: int
        How many replays to load for each map.
    Notes
    -----
    :meth:`~.load_info` is an expensive operation for large databases
    (likely because of inefficient sql queries). Consider using as few instances
    of this object as possible.
    """
    def __init__(self, path, num_maps, num_replays):
        super().__init__(False)
        self.path = path
        self.num_maps = num_maps
        self.limit = num_replays * num_maps
        self.replays = []
        conn = sqlite3.connect(path)
        self.cursor = conn.cursor()

    def load_info(self, loader):
        if self.info_loaded:
            return
        map_ids = self.cursor.execute(
            """
            SELECT DISTINCT map_id
            FROM replays
            """
        ).fetchall()
        # flatten map_ids, because it's actually a list of lists
        map_ids = [item[0] for item in map_ids]
        chosen_maps = random.choices(map_ids, k=self.num_maps)

        subclauses = [f"map_id = {chosen_map}" for chosen_map in chosen_maps]
        where_clause = " OR ".join(subclauses)

        # TODO LIMIT clause isn't quite right here, some maps will have less
        # than ``num_replays`` stored
        infos = self.cursor.execute(
            f"""
            SELECT user_id, map_id, replay_data, replay_id, mods
            FROM replays
            WHERE {where_clause}
            LIMIT {self.limit}
            """
        )

        for info in infos:
            r = CachedReplay(info[0], info[1], info[4], info[2], info[3])
            self.replays.append(r)
        self.info_loaded = True

    def all_replays(self):
        return self.replays

    def __eq__(self, other):
        return self.path == other.path


class ReplayDir(ReplayContainer):
    """
    A folder with replay files inside it.

    Notes
    -----
    Any files not ending in ``.osr`` are ignored.

    Warnings
    --------
    Nested directories are not support (yet). Any folders encountered will be
    ignored.
    """
    def __init__(self, dir_path, cache=None):
        super().__init__(cache)
        self.dir_path = Path(dir_path)
        if not self.dir_path.is_dir():
            raise ValueError(f"Expected path pointing to {self.dir_path} to be "
                              "a directory")
        self.replays = []

    def load_info(self, loader):
        if self.info_loaded:
            return
        for path in os.listdir(self.dir_path):
            if not path.endswith(".osr"):
                continue
            replay = ReplayPath(self.dir_path / path)
            self.replays.append(replay)
        self.info_loaded = True

    def all_replays(self):
        return self.replays

    def __eq__(self, other):
        return self.dir_path == other.dir_path


class Replay(Loadable):
    """
    A replay played by a player.

    Parameters
    ----------
    weight: :class:`~.enums.RatelimitWeight`
        How much it 'costs' to load this replay from the api.
    cache: bool
        Whether to cache this replay once it is loaded.

    Attributes
    ----------
    timestamp: :class:`datetime.datetime`
        When this replay was played.
    map_id: int
        The id of the map the replay was played on, or 0 if
        unknown or on an unsubmitted map.
    user_id: int
        The id of the player who played the replay, or 0 if unknown
        (if the player is restricted, for instance). Note that if the
        user id is known, even if the user is restricted, it should still be
        given instead of 0.
    username: str
        The username of the player who played the replay.
    mods: :class:`~.enums.ModCombination`
        The mods the replay was played with.
    replay_id: int
        The id of the replay, or 0 if the replay is unsubmitted.
    t: ndarray[int]
        A 1d array containing the timestamp for each frame. <br>
        This is only nonnull after the replay has been loaded.
    xy: ndarray[float]
        A 2d, two column array, containing the ``x`` and ``y`` coordinates of
        each frame in the first and second column respectively. <br>
        This is only nonnull after the replay has been loaded.
    k: ndarray[int]
        A 1d array containing the keys pressed for each frame. <br>
        This is only nonnull after the replay has been loaded.
    """
    def __init__(self, weight, cache):
        super().__init__(cache)
        self.weight = weight

        # remains ``None`` until replay is loaded
        self.timestamp   = None
        self.map_id      = None
        self.username    = None
        self.user_id     = None
        self.mods        = None
        self.replay_id   = None
        self.replay_data = None

        # remains ``None``` when replay is unloaded or loaded but with no data
        self.t = None
        self.xy = None
        self.k = None

    def _process_replay_data(self, replay_data):
        """
        Preprocesses the replay data (turns it into numpy arrays) for fast
        manipulation when investigating.

        Paramters
        ---------
        replay_data: list[:class:`~circleparse.Replay.ReplayEvent`]
            A list of :class:`~circleparse.Replay.ReplayEvent` objects,
            representing the actual data of the replay. If the replay could not
            be loaded, this should be ``None``.

        Notes
        -----
        This method must be called before a replay can be considered loaded
        (ie before you set ``loaded`` to ``True``).
        """
        self.replay_data = replay_data
        # replay wasn't available, can't preprocess the data
        if replay_data is None:
            return

        # remove invalid zero time frame at beginning of replay
        # https://github.com/ppy/osu/blob/1587d4b26fbad691242544a62dbf017a78705ae3/osu.Game/Scoring/Legacy/LegacyScoreDecoder.cs#L242-L245
        if replay_data[0].time_since_previous_action == 0:
            replay_data = replay_data[1:]

        # t, x, y, k
        data = [[], [], [], []]
        ## TODO try to use a peekable iterator to use an iter for above as well
        # use an iter an an optimization so we don't recreate the list when
        # taking (and removing) the first element
        replay_data = iter(replay_data)
        # The following is guesswork, but seems to accurately describe replays.
        # This references the "first" frame assuming that we have already
        # removed the truly first zero time frame, if it is present. So
        # technically the "first" frame below is the second frame.
        # There are two possibilities for osrs:
        # * for replays with a skip in the beginning, the first frame time is
        #   the skip duration. The next frame after that will have a negative
        #   time, to account for the replay data before the skip.
        # * for replays without a skip in the beginning, the firstframe time is
        #   -1.
        # Since in the first case the first frame time is positive, it would
        # cause our loop below to ignore the negative time frame afterwards,
        # throwing off the replay. To solve this we initiaize the running time
        # to the first frame's time.
        running_t = next(replay_data).time_since_previous_action
        # negative frame times are valid when they're at the beginning of a
        # replay (they're frames from before the start of the mp3 at t=0).
        # Count all negative frames until we hit our first positive one, and
        # ignore any negative frames after (eg in the middle of the replay).
        positive_seen = False

        for e in replay_data:
            e_t = e.time_since_previous_action
            # lazer ignores frames with negative time, but still adds it to the running time
            # https://github.com/ppy/osu/blob/1587d4b26fbad691242544a62dbf017a78705ae3/osu.Game/Scoring/Legacy/LegacyScoreDecoder.cs#L247-L250
            if e_t < 0:
                if not positive_seen:
                    running_t += e_t
                continue
            else:
                positive_seen = True
            running_t += e_t

            data[0].append(running_t)
            data[1].append(e.x)
            data[2].append(e.y)
            data[3].append(e.keys_pressed)

        block = np.array(data)

        t = np.array(block[0], dtype=int)
        xy = np.array([block[1], block[2]], dtype=float).T
        k = np.array(block[3], dtype=int)

        # sort our data by t. Stable so we don't reorder frames with equal times
        t_sort = np.argsort(t, kind="stable")
        t = t[t_sort]
        xy = xy[t_sort]
        k = k[t_sort]

        self.t = t
        self.xy = xy
        self.k = k

    def __repr__(self):
        return (f"Replay(timestamp={self.timestamp},map_id={self.map_id},user_id={self.user_id},mods={self.mods},"
               f"replay_id={self.replay_id},weight={self.weight},loaded={self.loaded},username={self.username})")

    def __str__(self):
        return f"Replay by {self.username} on {self.map_id}"


class ReplayMap(Replay):
    """
    A :class:`~.Replay` that was submitted to online servers.

    Parameters
    ----------
    map_id: int
        The id of the map the replay was played on.
    user_id: int
        The id of the player who played the replay.
    mods: ModCombination
        The mods the replay was played with. If ``None``, the
        highest scoring replay of ``user_id`` on ``map_id`` will be loaded,
        regardless of mod combination. Otherwise, the replay with ``mods``
        will be loaded.
    cache: bool
        Whether to cache this replay once it is loaded.
    """

    def __init__(self, map_id, user_id, mods=None, cache=None, info=None):
        super().__init__(RatelimitWeight.HEAVY, cache)
        self.log = logging.getLogger(__name__ + ".ReplayMap")
        self.map_id = map_id
        self.user_id = user_id
        self.mods = mods
        self.info = info
        if info:
            self.timestamp = info.timestamp
            self.map_id = info.map_id
            self.user_id = info.user_id
            self.username = info.username
            self.replay_id = info.replay_id
            self.mods = info.mods

    def load(self, loader, cache):
        """
        Loads the data for this replay from the api.

        Parameters
        ----------
        loader: :class:`~.loader.Loader`
            The :class:`~.loader.Loader` to load this replay with.
        cache: bool
            Whether to cache this replay after loading it. This only has an
            effect if ``self.cache`` is unset (``None``).

        Notes
        -----
        If ``replay.loaded`` is ``True``, this method has no effect.
        ``replay.loaded`` is set to ``True`` after this method is finished.
        """
        # only listen to the parent's cache if ours is not set. Lower takes precedence
        cache = cache if self.cache is None else self.cache
        self.log.debug("Loading %r", self)
        if self.loaded:
            self.log.debug("%s already loaded, not loading", self)
            return
        if self.info:
            info = self.info
        else:
            info = loader.replay_info(self.map_id, user_id=self.user_id, mods=self.mods)

        self.timestamp = info.timestamp
        self.username = info.username
        self.mods = info.mods
        self.replay_id = info.replay_id

        replay_data = loader.replay_data(info, cache=cache)
        self._process_replay_data(replay_data)
        self.loaded = True
        self.log.log(TRACE, "Finished loading %s", self)

    def __eq__(self, loadable):
        """
        Warning
        -------
        This equality check does not take into account attributes such as
        ``cache``. This is intentional - equality here means "do they represent
        the same replay".

        TODO possible false positive if a user overwrites their score inbetween
        loading two otherwise identical replay maps. Similar situation to
        ReplayPath equality. Could equality check replay data instead if both
        are loaded.
        """
        if not isinstance(loadable, ReplayMap):
            return False
        return self.map_id == loadable.map_id and self.user_id == loadable.user_id and self.mods == loadable.mods

    def __repr__(self):
        if self.loaded:
            return (f"ReplayMap(timestamp={self.timestamp},map_id={self.map_id},user_id={self.user_id},mods={self.mods},"
                f"cache={self.cache},replay_id={self.replay_id},loaded={self.loaded},username={self.username})")
        else:
            return (f"ReplayMap(map_id={self.map_id},user_id={self.user_id},mods={self.mods},cache={self.cache},"
                    f"loaded={self.loaded})")

    def __str__(self):
        return f"{'Loaded' if self.loaded else 'Unloaded'} ReplayMap by {self.user_id} on {self.map_id}"


class ReplayPath(Replay):
    """
    A :class:`~.Replay` saved locally in a ``.osr`` file.

    Parameters
    ----------
    path: str or :class:`os.PathLike`
        The path to the replay file.
    cache: bool
        Whether to cache this replay once it is loaded. Note that currently
        we do not cache :class:`~.ReplayPath` regardless of this parameter.
    """

    def __init__(self, path, cache=None):
        super().__init__(RatelimitWeight.LIGHT, cache)
        self.log = logging.getLogger(__name__ + ".ReplayPath")
        self.path = path
        self.hash = None

    def load(self, loader, cache):
        """
        Loads the data for this replay from the osr file.

        Parameters
        ----------
        loader: :class:`~.loader.Loader`
            The :class:`~.loader.Loader` to load this replay with.
        cache: bool
            Whether to cache this replay after loading it. This only has an
            effect if ``self.cache`` is unset (``None``). Note that currently
            we do not cache :class:`~.ReplayPath` regardless of this parameter.

        Notes
        -----
        If ``replay.loaded`` is ``True``, this method has no effect.
        ``replay.loaded`` is set to ``True`` after this method is finished.
        """

        # we don't cache local replays currently. Ignore cache option for if/when we need it
        self.log.debug("Loading ReplayPath %r", self)
        if self.loaded:
            self.log.debug("%s already loaded, not loading", self)
            return

        loaded = circleparse.parse_replay_file(self.path)
        self.timestamp = loaded.timestamp
        self.map_id = loader.map_id(loaded.beatmap_hash)
        self.username = loaded.player_name
        # TODO make this lazy loaded so we don't waste an api call
        self.user_id = loader.user_id(loaded.player_name)
        self.mods = Mod(loaded.mod_combination)
        self.replay_id = loaded.replay_id
        self.hash = loaded.beatmap_hash

        self._process_replay_data(loaded.play_data)
        self.loaded = True
        self.log.log(TRACE, "Finished loading %s", self)

    def __eq__(self, loadable):
        """
        Warnings
        --------
        XXX replays with the same path but different replay data (because the
        file at the path got changed for one but not the other) will return
        True in an equality check when they are not necessarily representing
        the same replay.

        TODO possible solution - check replay_data equality if both are loaded?
        might be unexpected behavior to some
        ```
        r1 = ReplayPath("./1.osr")
        cg.load(r1)
        # change the file located at ./1.osr to another osr file
        r2 = ReplayPath("./1.osr")
        cg.load(r2)
        r1 == r2 # True, but they contain different replay_data
        ```
        """
        if not isinstance(loadable, ReplayPath):
            return False
        return self.path == loadable.path

    def __repr__(self):
        if self.loaded:
            return (f"ReplayPath(path={self.path},map_id={self.map_id},user_id={self.user_id},mods={self.mods},"
                    f"replay_id={self.replay_id},weight={self.weight},loaded={self.loaded},username={self.username})")
        else:
            return f"ReplayPath(path={self.path},weight={self.weight},loaded={self.loaded})"

    def __str__(self):
        if self.loaded:
            return f"Loaded ReplayPath by {self.username} on {self.map_id} at {self.path}"
        else:
            return f"Unloaded ReplayPath at {self.path}"


class ReplayID(Replay):
    def __init__(self, replay_id, cache=None):
        super().__init__(RatelimitWeight.HEAVY, cache)
        self.replay_id = replay_id

    def load(self, loader, cache):
        # TODO file github issue about loading info from replay id,
        # right now we can literally only load the replay data which
        # is pretty useless if we don't have a map id or the mods used
        cache = cache if self.cache is None else self.cache
        replay_data = loader.replay_data_from_id(self.replay_id, cache)
        self._process_replay_data(replay_data)
        self.loaded = True

    def __eq__(self, other):
        return self.replay_id == other.replay_id


class CachedReplay(Replay):
    def __init__(self, user_id, map_id, mods, replay_data, replay_id):
        super().__init__(RatelimitWeight.NONE, False)
        self.user_id = user_id
        self.map_id = map_id
        self.mods = Mod(mods)
        self.replay_data = replay_data
        self.replay_id = replay_id

    def load(self, loader, cache):
        if self.loaded:
            return
        decompressed = wtc.decompress(self.replay_data)
        replay_data = circleparse.parse_replay(decompressed, pure_lzma=True).play_data
        self._process_replay_data(replay_data)
        self.loaded = True

    def __eq__(self, other):
        # could check more but replay_id is already a primary key, guaranteed unique
        return self.replay_id == other.replay_id
