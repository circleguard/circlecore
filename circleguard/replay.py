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
        pass

    @abc.abstractmethod
    def load(self, loader, cache):
        """
        Loads the information this loadable needs to become fully loaded.
        Details left to the subclass implementation.

        Parameters
        ----------
        loader: :class:`~circleguard.loader.Loader`
            The loader to load this replay with. Although subclasses may not
            end up using a :class:`~circleguard.loader.Loader` to
            properly load the replay (if they don't load anything from the osu
            api, for instance), the parameter is necessary for homogeneity
            among method calls.
        cache: bool
            Whether the loadable should cache their replay data. This argument
            comes from a parent—either a :class:`~.InfoLoadable` or
            :class:`~circleguard.circleguard.Circleguard` itself. Should the
            loadable already have a ``cache`` attribute, that should take
            precedence over the option passed in this method, but if the
            loadable has no preference then it should listen to the ``cache``
            here.
        """
        pass

    @abc.abstractmethod
    def num_replays(self):
        pass

    @abc.abstractmethod
    def all_replays(self):
        pass

class InfoLoadable(abc.ABC):
    """
    A loadable which has an info loaded stage, between unloaded and loaded.

    When info loaded, the :class:`~InfoLoadable` has :class:`Loadable`\s but
    they are unloaded.
    """
    def __init__(self):
        pass

    @abc.abstractmethod
    def load_info(self, loader):
        pass

class ReplayContainer(InfoLoadable):
    """
    Holds a list of Replays, in addition to being a :class:`~Loadable`.

    ReplayContainer's start unloaded and become info loaded when
    :meth:`~ReplayContainer.load_info` is called. They become fully
    loaded when :meth:`~ReplayContainer.load`
    is called (and if this is called when the ReplayContainer is in the
    unloaded state, :meth:`~ReplayContainer.load` will load info first,
    then load the replays.)

    In the unloaded state, the container has no actual Replay objects. It may
    have limited knowledge about their number or type.

    In the info loaded state, the container has references to Replay objects,
    but those Replay objects are unloaded.

    In the loaded state, the Replay objects are loaded.
    """
    @abc.abstractmethod
    def __getitem__(self, key):
        pass

    @abc.abstractmethod
    def __iter__(self):
        pass

class Check(InfoLoadable):
    """
    Organizes :class:`~.Loadable`\s and what to investigate them for.

    Parameters
    ----------
    loadables: :class:`~.Loadable`
        The loadables to hold for investigation.
    detect: :class:`~.Detect`
        What cheats to investigate for.
    loadables2: :class:`~.Loadable`

        Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
    """

    def __init__(self, loadables, detect, loadables2=None, cache=None):
        self.log = logging.getLogger(__name__ + ".Check")
        self.loadables = [loadables] if isinstance(loadables, Loadable) else loadables
        self.loadables2 = [loadables2] if isinstance(loadables2, Loadable) else [] if loadables2 is None else loadables2
        self.cache = cache
        self.detect = detect
        self.loaded = False

    def all_loadables(self):
        """
        Returns all the :class:`~circleguard.replay.Loadable`\s contained by
        this class.

        Returns
        -------
        list[:class:`~circleguard.replay.Loadable`]
            All loadables in this class.

        See Also
        --------
        :func:`~circleguard.replay.Loadable.all_replays` and
        :func:`~circleguard.replay.Loadable.all_replays2`
        Notes
        -----
        :class:`~circleguard.replay.Loadable`\s are very different from
        :class:`~circleguard.replay.Replay`\s -
        ``len(container.all_loadables())`` will *not* return the number of
        replays in the container, for instance.
        """
        return self.loadables + self.loadables2

    def load(self, loader, cache=None):
        """
        Loads all :class:`~circleguard.replay.Loadable`\s in this Container.

        Parameters
        ----------
        loader: :class:`~circleguard.loader.Loader`
            The loader to load the :class:`~circleguard.replay.Loadable`\s with.
        """
        # cache arg only for homogeneity with func calls. No effect
        for loadable in self.all_loadables():
            loadable.load(loader, cache=self.cache)

    def load_info(self, loader):
        for loadable in self.all_loadables():
            if isinstance(loadable, InfoLoadable):
                loadable.load_info(loader)

    def num_replays(self):
        num = 0
        for loadable in self.all_loadables():
            num += loadable.num_replays()
        return num

    def all_replays(self):
        replays = []
        for loadable in self.loadables:
            replays += loadable.all_replays()
        return replays

    def all_replays2(self):
        replays2 = []
        for loadable in self.loadables2:
            replays2 += loadable.all_replays()
        return replays2

    def __add__(self, other):
        self.loadables.append(other)
        return Check(self.loadables, self.loadables2, self.cache, self.detect)

    def __repr__(self):
        return (f"Check(loadables={self.loadables},loadables2={self.loadables2},cache={self.cache},"
                f"detect={self.detect},loaded={self.loaded})")

class Map(ReplayContainer):
    def __init__(self, map_id, num=None, span=None, mods=None, cache=None):
        if not bool(num) ^ bool(span):
            # technically, num and span both being set would *work*, just span
            # would override. But this avoids any confusion.
            raise ValueError("One of num or span must be specified, but not both")
        self.replays = []
        self.cache = cache
        self.map_id = map_id
        self.num = num
        self.mods = mods
        self.span = span
        self.loaded = False

    def load_info(self, loader):
        if self.replays:
            # dont load twice
            return
        for info in loader.user_info(self.map_id, num=self.num, mods=self.mods, span=self.span):
            self.replays.append(ReplayMap(info.map_id, info.user_id, info.mods, cache=self.cache))

    def load(self, loader, cache):
        # only listen to the parent's cache if ours is not set. Lower takes precedence
        cascade_cache = cache if self.cache is None else self.cache
        self.load_info(loader)
        for replay in self.replays:
            replay.load(loader, cascade_cache)

    def num_replays(self):
        if self.replays:
            return len(self.replays)
        elif self.span:
            return len(span_to_list(self.span))
        else:
            return self.num

    def all_replays(self):
        return self.replays


    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.replays[key.start:key.stop:key.step]
        else:
            return self.replays[key]

    def __iter__(self):
        return iter(self.replays)

    def __repr__(self):
        return (f"Map(map_id={self.map_id},num={self.num},cache={self.cache},mods={self.mods},"
                f"span={self.span},replays={self.replays},loaded={self.loaded})")

    def __str__(self):
        return f"Map {self.map_id}"


class User(ReplayContainer):
    def __init__(self, user_id, num=None, span=None, mods=None, cache=None, available_only=True):
        if not bool(num) ^ bool(span):
            raise ValueError("One of num or span must be specified, but not both")
        self.replays = []
        self.user_id = user_id
        self.num = num
        self.span = span
        self.mods = mods
        self.cache = cache
        self.available_only = available_only

    def load_info(self, loader):
        if self.replays:
            return
        for info in loader.get_user_best(self.user_id, num=self.num, span=self.span, mods=self.mods):
            if self.available_only and not info.replay_available:
                continue
            self.replays.append(ReplayMap(info.map_id, info.user_id, info.mods, cache=self.cache, info=info))

    def load(self, loader, cache):
        # only listen to the parent's cache if ours is not set. Lower takes precedence
        cascade_cache = cache if self.cache is None else self.cache
        self.load_info(loader)
        for loadable in self.replays:
            loadable.load(loader, cascade_cache)

    def num_replays(self):
        if self.replays:
            return len(self.replays)
        elif self.span:
            return len(span_to_list(self.span))
        else:
            return self.num

    def all_replays(self):
        replays = []
        for loadable in self.replays:
            replays += loadable.all_replays()
        return replays

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.replays[key.start:key.stop:key.step]
        else:
            return self.replays[key]

    def __iter__(self):
        return iter(self.replays)


class Replay(Loadable):
    """
    A replay played by a player.

    Parameters
    ----------
    timestamp: Datetime
        When this replay was played.
    map_id: int
        The id of the map the replay was played on, or 0 if
        unknown or on an unsubmitted map.
    user_id: int
        The id of the player who played the replay, or 0 if
        unknown (if the player is restricted, for instance).
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
        How much it 'costs' to load this replay from the api. If the load method
        of the replay makes no api calls, this value is RatelimitWeight.NONE.
        If it makes only light api calls (anything but /api/get_replay),
        this value isRatelimitWeight.LIGHT. If it makes any heavy api calls
        (/api/get_replay), this value is RatelimitWeight.HEAVY.
        See the RatelimitWeight documentation for more details.
    """
    def __init__(self, timestamp, map_id, username, user_id, mods, replay_id, replay_data, weight):
        self.timestamp = timestamp
        self.map_id = map_id
        self.username = username
        self.user_id = user_id
        self.mods = mods
        self.replay_id = replay_id
        self.replay_data = replay_data
        self.weight = weight
        self.loaded = True


    def num_replays(self):
        return 1

    def all_replays(self):
        return [self]

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
        list[tuple(int, float, float, something)]
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
    A :class:`~.Replay` that was submitted to online servers (and is thus tied
    to a map).

    Parameters
    ----------
    map_id: int
        The id of the map the replay was played on.
    user_id: int
        The id of the player who played the replay.
    mods: ModCombination
        The mods the replay was played with. If `None`, the
        highest scoring replay of ``user_id`` on ``map_id`` will be loaded,
        regardless of mod combination. Otherwise, the replay with ``mods``
        will be loaded.
    detect: :class:`~.enums.Detect`
        What cheats to run tests to detect.
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

    def __repr__(self):
        if self.loaded:
            return (f"ReplayMap(timestamp={self.timestamp},map_id={self.map_id},user_id={self.user_id},mods={self.mods},"
                f"cache={self.cache},replay_id={self.replay_id},loaded={self.loaded},username={self.username})")

        else:
            return (f"ReplayMap(map_id={self.map_id},user_id={self.user_id},mods={self.mods},cache={self.cache},"
                    f"loaded={self.loaded})")

    def __str__(self):
        return f"{'Loaded' if self.loaded else 'Unloaded'} ReplayMap by {self.user_id} on {self.map_id}"

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
        if(self.loaded):
            self.log.debug("%s already loaded, not loading", self)
            return
        if self.info:
            info = self.info
        else:
            info = loader.user_info(self.map_id, user_id=self.user_id, mods=self.mods)
        replay_data = loader.replay_data(info, cache=cache)
        Replay.__init__(self, info.timestamp, self.map_id, info.username, self.user_id, info.mods, info.replay_id, replay_data, self.weight)
        self.log.log(TRACE, "Finished loading %s", self)


class ReplayPath(Replay):
    """
    A :class:`~.Replay` saved locally in an ``osr`` file.

    Parameters
    ----------
    path: str or :class`os.PathLike`
        The path to the replay file.
    cache: bool
        Whether to cache this replay once it is loaded. Note that currently
        we do not cache :class:`~.ReplayPath` regardless of this parameter.
    """

    def __init__(self, path, cache=None):
        self.log = logging.getLogger(__name__ + ".ReplayPath")
        self.path = path
        self.cache = cache
        self.weight = RatelimitWeight.LIGHT
        self.loaded = False

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

        Replay.__init__(self, loaded.timestamp, map_id, loaded.player_name, user_id, ModCombination(loaded.mod_combination),
                        loaded.replay_id, loaded.play_data, self.weight)
        self.log.log(TRACE, "Finished loading %s", self)
