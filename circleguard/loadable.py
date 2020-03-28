import abc
import logging

import circleparse
import numpy as np

from circleguard.enums import RatelimitWeight, ModCombination
from circleguard.utils import TRACE, span_to_list


class Loadable(abc.ABC):
    """
    An object that has further information that can be loaded;
    from the osu api, local cache, or some other location.

    Notes
    -----
    This is an abstract class and cannot be directly instantiated.
    """
    def __init__(self):
        self.loaded = False

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
            Whether the loadable should cache their replay data. This argument
            comes from a parent—either a :class:`~.LoadableContainer` or
            :class:`~circleguard.circleguard.Circleguard` itself. Should the
            loadable already have a ``cache`` attribute, that should take
            precedence over the option passed in this method, but if the
            loadable has no preference then it should listen to the ``cache``
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

    When loaded, the :class:`~InfoLoadable` has loaded :class:`Loadable`\s.
    """
    def __init__(self, cache):
        super().__init__()
        self.cache = cache
        self.info_loaded = False

    @abc.abstractmethod
    def load_info(self, loader):
        pass

    @abc.abstractmethod
    def all_replays(self):
        pass

    # def __contains__(self, loadable):
    #     our_replays = self.all_replays()
    #     if isinstance(loadable, LoadableContainer):
    #         # if we contain all the Replays in the loadable container, we contain
    #         # the loadable container as well
    #         return all([replay in our_replays for replay in loadable.all_replays()])
    #     return loadable in our_replays

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
    A LoadableContainer guaranteed to only contain Replays and its subclasses.

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


class Check(LoadableContainer):
    """
    Organizes :class:`~.Loadable`\s and what to investigate them for.

    Parameters
    ----------
    loadables: :class:`~.Loadable`
        The loadables to hold for investigation.
    detect: :class:`~.Detect`
        What cheats to investigate for.
    loadables2: :class:`~.Loadable`
        A second set of loadables. Only used when :class:`~StealDetect` is
        passed in ``detect``. If passed, the loadables in ``loadables`` will
        not be compared to each other, but instead to each replay in
        ``loadables2``, for replay stealing.
    cache: bool
        Whether to cache the loadables once they are loaded. This will be
        overriden by a ``cache`` option set by a :class:`~Loadable` in
        ``loadables``. It only affects children loadables when they do not have
        a ``cache`` option set.
    """

    def __init__(self, loadables, detect, loadables2=None, cache=None):
        super().__init__(cache)
        self.log = logging.getLogger(__name__ + ".Check")
        self.loadables = [loadables] if isinstance(loadables, Loadable) else loadables
        self.loadables2 = [loadables2] if isinstance(loadables2, Loadable) else [] if loadables2 is None else loadables2
        self.detect = detect

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
        :func:`~Check.all_replays` and :func:`~Check.all_replays2`.

        Notes
        -----
        :class:`~circleguard.loadable.Loadable`\s are very different from
        :class:`~circleguard.loadable.Replay`\s -
        ``len(check.all_loadables())`` will *not* return the number of
        replays in the check, for instance.
        """
        return self.loadables + self.loadables2

    def load(self, loader, cache=None):
        """
        Loads all :class:`~circleguard.loadable.Loadable`\s in this check.

        Parameters
        ----------
        loader: :class:`~circleguard.loader.Loader`
            The loader to load the :class:`~circleguard.loadable.Loadable`\s with.
        """
        if self.loaded:
            return
        cascade_cache = cache if self.cache is None else self.cache
        self.load_info(loader)
        for loadable in self.all_loadables():
            loadable.load(loader, cascade_cache)
        self.loaded = True

    def load_info(self, loader):
        if self.info_loaded:
            return
        for loadable in self.all_loadables():
            if isinstance(loadable, LoadableContainer):
                loadable.load_info(loader)
        self.info_loaded = True

    def all_replays(self):
        return self.all_replays1() + self.all_replays2()

    def all_replays1(self):
        """
        Returns all the :class:`~.Replay`\s in this check. Contrast with
        :func:`~Check.all_loadables`, which returns all the
        :class:`~.Loadable`\s in this check.

        Warnings
        --------
        If you want an accurate list of :class:`~.Replay`\s in this check, you
        must call :func:`~circleguard.circleguard.Circleguard.load` on this
        :class:`~Check` before :func:`~Check.all_replays`.
        :class:`~.LoadableContainer`\s contained in this :class:`~Check` may not
        be info loaded otherwise, and thus do not have a complete list of the
        replays they represent.
        """
        replays = []
        for loadable in self.loadables:
            if isinstance(loadable, LoadableContainer):
                replays += loadable.all_replays()
            else:
                replays.append(loadable) # loadable is a Replay
        return replays

    def all_replays2(self):
        """
        Returns all the :class:`~.Replay`\s contained by ``replays2`` of this
        check.
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

    def __add__(self, other):
        self.loadables.append(other)
        # TODO why not just return ``self``?
        return Check(self.loadables, self.detect, self.loadables2, self.cache)

    def __repr__(self):
        return (f"Check(loadables={self.loadables},loadables2={self.loadables2},cache={self.cache},"
                f"detect={self.detect},loaded={self.loaded})")

class Map(ReplayContainer):
    """
    A map's top plays (leaderboard), as seen on the website.

    Parameters
    ----------
    map_id: int
        The map to represent the top plays for.
    num: int
        How many top plays on the map to represent, starting from the first
        place play. One of ``num`` or ``span`` must be passed, but not both.
    span: str
        A comma separated list of ranges of top plays to retrieve.
        ``span="1-3,6,2-4"`` -> replays in the range ``[1,2,3,4,6]``.
    mods: :class:`~.enums.ModCombination`
        If passed, only represent replays played with this exact mod
        combination. Due to limitations with the api, fuzzy matching is not
        implemented. <br>
        This is applied before ``num`` or ``span``. That is, if ``num=2``
        and ``mods=Mod.HD``, the top two ``HD`` plays on the map are
        represented.
    cache: bool
        Whether to cache the replays once they are loaded.
    """
    def __init__(self, map_id, num=None, span=None, mods=None, cache=None):
        super().__init__(cache)
        if not bool(num) ^ bool(span):
            # technically, num and span both being set would *work*, just span
            # would override. But this avoids any confusion.
            raise ValueError("One of num or span must be specified, but not both")
        self.replays = []
        self.map_id = map_id
        self.num = num
        self.mods = mods
        self.span = span

    def load_info(self, loader):
        if self.info_loaded:
            return
        for info in loader.replay_info(self.map_id, num=self.num, mods=self.mods, span=self.span):
            self.replays.append(ReplayMap(info.map_id, info.user_id, info.mods, cache=self.cache, info=info))
        self.info_loaded = True

    def load(self, loader, cache=None):
        if self.loaded:
            return
        # only listen to the parent's cache if ours is not set. Lower takes precedence
        cascade_cache = cache if self.cache is None else self.cache
        self.load_info(loader)
        for replay in self.replays:
            replay.load(loader, cascade_cache)
        self.loaded = True

    def all_replays(self):
        """
        Returns all the :class:`~.Replay`\s in this map.

        Warnings
        --------
        If you want an accurate list of :class:`~.Replay`\s in this map, you
        must call :func:`~circleguard.circleguard.Circleguard.load` on this map
        before :func:`~Map.all_replays`. Otherwise, this
        class is not info loaded, and does not have a complete list of replays
        it represents.
        """
        return self.replays

    def __eq__(self, loadable):
        if not isinstance(loadable, Map):
            return False
        return (self.map_id == loadable.map_id and self.num == loadable.num
                and self.mods == loadable.mods and self.span == loadable.span)

    def __repr__(self):
        return (f"Map(map_id={self.map_id},num={self.num},cache={self.cache},mods={self.mods},"
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
    num: int
        How many top plays of the user to represent, starting from their best
        play. One of ``num`` or ``span`` must be passed, but not both.
    span: str
        A comma separated list of ranges of top plays to retrieve.
        ``span="1-3,6,2-4"`` -> replays in the range ``[1,2,3,4,6]``.
    mods: :class:`~.enums.ModCombination`
        If passed, only represent replays played with this exact mod
        combination. Due to limitations with the api, fuzzy matching is not
        implemented. <br>
        This is applied before ``num`` or ``span``. That is, if ``num=2``
        and ``mods=Mod.HD``, the user's top two ``HD`` plays are represented.
    cache: bool
        Whether to cache the replays once they are loaded.
    available_only: bool
        Whether to represent only replays that have replay data available.
        Replays are filtered on this basis after ``mods`` and ``num``/``span``
        are applied. True by default.
    """
    def __init__(self, user_id, num=None, span=None, mods=None, cache=None, available_only=True):
        super().__init__(cache)
        if not bool(num) ^ bool(span):
            raise ValueError("One of num or span must be specified, but not both")
        self.replays = []
        self.user_id = user_id
        self.num = num
        self.span = span
        self.mods = mods
        self.available_only = available_only

    def load_info(self, loader):
        if self.info_loaded:
            return
        for info in loader.get_user_best(self.user_id, num=self.num, span=self.span, mods=self.mods):
            if self.available_only and not info.replay_available:
                continue
            self.replays.append(ReplayMap(info.map_id, info.user_id, info.mods, cache=self.cache, info=info))
        self.info_loaded = True

    def load(self, loader, cache=None):
        if self.loaded:
            return
        # only listen to the parent's cache if ours is not set. Lower takes precedence
        cascade_cache = cache if self.cache is None else self.cache
        self.load_info(loader)
        for loadable in self.replays:
            loadable.load(loader, cascade_cache)
        self.loaded = True

    def all_replays(self):
        """
        Returns all the :class:`~.Replay`\s in this user.

        Warnings
        --------
        If you want an accurate list of :class:`~.Replay`\s in this user, you
        must call :func:`~circleguard.circleguard.Circleguard.load` on this
        user before :func:`~User.all_replays`. Otherwise, this class is not
        info loaded, and does not have a complete list of replays it
        represents.
        """
        return self.replays


    def __eq__(self, loadable):
        if not isinstance(loadable, User):
            return False
        return (self.user_id == loadable.user_id and self.num == loadable.num
                and self.mods == loadable.mods and self.span == loadable.span)


class MapUser(ReplayContainer):
    """
    All replays on a map by a user, not just the top replay.

    Parameters
    ----------
    map_id: int
        The map to represent scores by `user_id` on.
    user_id: int
        The user to represent scores on `map_id` for.
    num: int
        How many plays by `user_id` on `map_id` to represent.
        One of ``num`` or ``span`` must be passed, but not both.
    span: str
        A comma separated list of ranges of plays to retrieve.
        ``span="1-3,6,2-4"`` -> replays in the range ``[1,2,3,4,6]``.
    cache: bool
        Whether to cache the replays once they are loaded.
    available_only: bool
        Whether to represent only replays that have replay data available.
        Replays are filtered on this basis after ``mods`` and ``num``/``span``
        are applied. True by default.
    """
    def __init__(self, map_id, user_id, num=None, span=None, cache=None, available_only=True):
        super().__init__(cache)
        if not bool(num) ^ bool(span):
            raise ValueError("One of num or span must be specified, but not both")
        self.replays = []
        self.map_id = map_id
        self.user_id = user_id
        self.num = num
        self.span = span
        self.available_only = available_only

    def load_info(self, loader):
        if self.info_loaded:
            return
        for info in loader.replay_info(self.map_id, num=self.num, span=self.span, user_id=self.user_id, limit=False):
            if self.available_only and not info.replay_available:
                continue
            self.replays.append(ReplayMap(info.map_id, info.user_id, info.mods, cache=self.cache, info=info))
        self.info_loaded = True

    def load(self, loader, cache=None):
        if self.loaded:
            return
        # only listen to the parent's cache if ours is not set. Lower takes precedence
        cascade_cache = cache if self.cache is None else self.cache
        self.load_info(loader)
        for loadable in self.replays:
            loadable.load(loader, cascade_cache)
        self.loaded = True

    def all_replays(self):
        """
        Returns all the :class:`~.Replay`\s in this MapUser.

        Warnings
        --------
        If you want an accurate list of :class:`~.Replay`\s in this MapUser,
        you must call :func:`~circleguard.circleguard.Circleguard.load` on this
        MapUser before :func:`~.all_replays`. Otherwise, this class is not info
        loaded, and does not have a complete list of replays it represents.
        """
        return self.replays

    def __eq__(self, loadable):
        if not isinstance(loadable, MapUser):
            return False
        return (self.map_id == loadable.map_id and self.user_id == loadable.user_id
                and self.num == loadable.num and self.span == loadable.span)


class Replay(Loadable):
    """
    A replay played by a player.

    Parameters
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
    replay_data: list[:class:`~circleparse.Replay.ReplayEvent`]
        A list of :class:`~circleparse.Replay.ReplayEvent` objects, representing
        the actual data of the replay. If the replay could not be loaded, this
        should be ``None``.
    weight: :class:`~.enums.RatelimitWeight`
        How much it 'costs' to load this replay from the api.
    """
    def __init__(self, timestamp, map_id, username, user_id, mods, replay_id, replay_data, weight):
        super().__init__()
        self.timestamp = timestamp
        self.map_id = map_id
        self.username = username
        self.user_id = user_id
        self.mods = mods
        self.replay_id = replay_id
        self.replay_data = replay_data
        self.weight = weight
        self.loaded = True

        block = list(zip(*[(e.time_since_previous_action, e.x, e.y, e.keys_pressed) for e in self.replay_data]))

        t = np.array(block[0], dtype=int).cumsum()
        xy = np.array([block[1], block[2]], dtype=float).T
        k = np.array(block[3], dtype=int)

        t, t_sort = np.unique(t, return_index=True)
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

    def as_list_with_timestamps(self):
        """
        Gets this replay's play data as a list of tuples of absolute time,
        x, y, and pressed keys for each event in the data.

        Returns
        -------
        list[tuple(int, float, float, int)]
            A list of tuples of (t, x, y, keys) for each event
            in the replay data.
        """
        # get all offsets sum all offsets before it to get all absolute times
        timestamps = np.array([e.time_since_previous_action for e in self.replay_data])
        timestamps = timestamps.cumsum()

        # zip timestamps back to data and convert t, x, y, keys to tuples
        txyk = [[z[0], z[1].x, z[1].y, z[1].keys_pressed] for z in zip(timestamps, self.replay_data)]
        # sort to ensure time goes forward as you move through the data
        # in case someone decides to make time go backwards anyway
        txyk.sort(key=lambda p: p[0])
        return txyk


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
        self.log = logging.getLogger(__name__ + ".ReplayMap")
        self.map_id = map_id
        self.user_id = user_id
        self.mods = mods
        self.cache = cache
        self.info = info
        self.weight = RatelimitWeight.HEAVY
        self.loaded = False

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
        replay_data = loader.replay_data(info, cache=cache)
        Replay.__init__(self, info.timestamp, self.map_id, info.username, self.user_id, info.mods, info.replay_id, replay_data, self.weight)
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
        self.log = logging.getLogger(__name__ + ".ReplayPath")
        self.path = path
        self.hash = None
        self.cache = cache
        self.weight = RatelimitWeight.LIGHT
        self.loaded = False

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
        map_id = loader.map_id(loaded.beatmap_hash)
        user_id = loader.user_id(loaded.player_name)
        self.hash = loaded.beatmap_hash

        Replay.__init__(self, loaded.timestamp, map_id, loaded.player_name, user_id, ModCombination(loaded.mod_combination),
                        loaded.replay_id, loaded.play_data, self.weight)
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
