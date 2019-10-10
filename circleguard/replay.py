import abc
import logging

import circleparse
import numpy as np

from circleguard.enums import Detect, RatelimitWeight
from circleguard import config
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
    def load(self, loader):
        """
        Loads the information this loadable needs. Details left to the
        subclass implementation.

        Parameters
        ----------
        loader: :class:`~circleguard.loader.Loader`
            The loader to load this replay with. Although subclasses may not
            end up using a :class:`~circleguard.loader.Loader` to
            properly load the replay (if they don't load anything from the osu
            api, for instance), the parameter is necessary for homogeneity among
            method calls.
        """
        pass

    def filter(self, loader, include):
        """
        Whether this :class:`~circleguard.replay.Loadable` should be loaded,
        as determined by some criterion of the function ``include``.

        Parameters
        ----------
        loader: :class:`~circleguard.loader.Loader`
            This parameter will not be used except in
            :func:`~circleguard.replay.Map.filter` - an unfortunate necessity of
            the current hierarchy.
        include: function(:class:`~circleguard.replay.Replay`)
            A predicate function that returns True if the replay should be
            loaded, and False otherwise. The function must accept a single
            argument - a :class:`~circleguard.replay.Replay`, or one of its
            subclasses.
        """
        return include(self)

class Container(Loadable, abc.ABC):
    """
    Containers hold :class:`~circleguard.replay.Loadable`\s, managing their
    loading, setting cascading, and other low level aspects.

    Parameters
    ----------
    loadables: list[:class:`~circleguard.replay.Loadable`]
        The loadables to load, investigate, and manage through this Container.
    cache: bool
        Whether or not to cache the replays upon loading them.
        Defaults to False.
    steal_thresh: int
        If a comparison scores below this value, it is considered cheated.
        Defaults to 18.
    rx_thresh: int
        If a replay has a ur below this value, it is considered cheated.
        Defaults to 50.
    include: Function(:class:`~circleguard.replay.Replay`)
        A predicate function that returns True if the replay should be loaded,
        and False otherwise. The function must accept a single argument -
        a :class:`~circleguard.replay.Replay`, or one of its subclasses.
    detect: :class:`~circleguard.enums.Detect`
        What cheats to run tests to detect. This will only overwrite replay's settings in this Check
        if the replays were not given a Detect different from the (default) config value.

    Notes
    -----
    Containers themselves are a :class:`~circleguard.replay.Loadable`, and so
    a Container may be instantiated with other Containers in its loadable
    argument. This is an intentional design choice and is fully supported.
    """

    def __init__(self, loadables, loadables2=None, cache=None, steal_thresh=None, rx_thresh=None, include=None, detect=None):
        self.log = logging.getLogger(__name__ + ".Container")
        self.loadables = loadables if loadables else []
        self.loadables2 = loadables2 if loadables2 else []
        self.cache = cache if cache else config.cache
        self.steal_thresh = steal_thresh if steal_thresh else config.steal_thresh
        self.rx_thresh = rx_thresh if rx_thresh else config.rx_thresh
        self.include = include if include else config.include
        self.detect = detect if detect else config.detect
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

    def load(self, loader):
        """
        Loads all :class:`~circleguard.replay.Loadable`\s in this Container.

        Parameters
        ----------
        loader: :class:`~circleguard.loader.Loader`
            The loader to load the :class:`~circleguard.replay.Loadable`\s with.
        """
        for loadable in self.all_loadables():
            loadable.load(loader)

    def filter(self, loader, predicate=None):
        predicate = self.include if predicate is None else predicate
        self.loadables = [l for l in self.loadables if l.filter(loader, predicate)]
        self.loadables2 = [l for l in self.loadables2 if l.filter(loader, predicate)]

    @abc.abstractclassmethod
    def num_replays(self):
        ...

    def all_replays(self):
        replays = []
        for loadable in self.loadables:
            if isinstance(loadable, Container):
                replays += loadable.all_replays()
            else:
                replays.append(loadable)
        return replays

    def all_replays2(self):
        replays2 = []
        for loadable in self.loadables2:
            if isinstance(loadable, Container):
                replays2 += loadable.all_replays2()
            else:
                replays2.append(loadable)
        return replays2

    def cascade_options(self, cache, steal_thresh, rx_thresh, detect):
        self.cache = cache if self.cache == config.cache else self.cache
        self.steal_thresh = steal_thresh if self.steal_thresh == config.steal_thresh else self.steal_thresh
        self.rx_thresh = rx_thresh if self.rx_thresh == config.rx_thresh else self.rx_thresh
        self.detect = detect if self.detect == config.detect else self.detect
        for loadable in self.all_loadables():
            loadable.cascade_options(cache, steal_thresh, rx_thresh, detect)

class Map(Container):
    def __init__(self, map_id, num=None, cache=None, steal_thresh=None, rx_thresh=None, include=None, mods=None, detect=None, span=None):
        super().__init__(None, None, cache, steal_thresh, rx_thresh, include, detect)
        self.map_id = map_id
        self.num = num
        self.mods = mods
        self.span = span
        self.loaded = False

    def load_info(self, loader):
        if self.loadables:
            # dont load twice
            return
        infos = loader.user_info(self.map_id, num=self.num, mods=self.mods, span=self.span)
        self.loadables = [ReplayMap(info.map_id, info.user_id, info.mods, detect=self.detect) for info in infos]
        self.cascade_options(self.cache, self.steal_thresh, self.rx_thresh, self.detect)


    def load(self, loader):
        self.load_info(loader)
        for replay in self.loadables:
            replay.load(loader)

    def filter(self, loader, predicate=None):
        predicate = self.include if predicate is None else predicate
        self.load_info(loader)
        self.loadables = [replay for replay in self.loadables if replay.filter(loader, predicate)]
        return True

    def num_replays(self):
        """
        Returns the number of Replays (not Loadables) in this class. Adds up
        the number of replays + container.num_replays for each container.
        """
        if self.loadables:
            return len(self.loadables)
        elif self.span:
            return len(span_to_list(self.span))
        else:
            return self.num

    def __repr__(self):
        return (f"Map(map_id={self.map_id},num={self.num},cache={self.cache},mods={self.mods},"
                f"detect={self.detect},span={self.span},loadables={self.loadables},loaded={self.loaded})")

class Check(Container):
    """
    A simple :class:`~.Container` that holds an arbitrary
    amount and type of loadables.

    Parameters
    ----------
    loadables: list[:class:`~.Loadable`]
        The loadables to load, investigate, and manage through this Container.
    cache: bool
        Whether or not to cache the replays upon loading them.
        Defaults to False.
    steal_thresh: int
        If a comparison scores below this value, it is considered cheated.
        Defaults to 18.
    rx_thresh: int
        If a replay has a ur below this value, it is considered cheated.
        Defaults to 50.
    include: Function(:class:`~.Replay`)
        A predicate function that returns True if the replay should be loaded,
        and False otherwise. The function must accept a single argument -
        a :class:`~.Replay`, or one of its subclasses.
    detect: :class:`~.enums.Detect`
        What cheats to run tests to detect. This will only overwrite replay's settings in this Check
        if the replays were not given a Detect different from the (default) config value.
    """

    def __init__(self, loadables, loadables2=None, cache=None, steal_thresh=None, rx_thresh=None, include=None, detect=None):
        super().__init__(loadables, loadables2, cache, steal_thresh, rx_thresh, include, detect)
        self.cascade_options(self.cache, self.steal_thresh, self.rx_thresh, self.detect)

    def num_replays(self):
        num = 0
        for loadable in self.all_loadables():
            if isinstance(loadable, Container):
                num += loadable.num_replays()
            else:
                num += 1
        return num


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
    mods: int
        The bitwise mod combination the replay was played with.
    replay_id: int
        The id of the replay, or 0 if the replay is unsubmitted.
    replay_data: list[:class:`~circleparse.Replay.ReplayEvent`]
        A list of :class:`~circleparse.Replay.ReplayEvent` objects, representing
        the actual data of the replay. If the replay could not be loaded, this
        should be ``None``.
    detect: :class:`~.enums.Detect`
        What cheats to run tests to detect.
    weight: :class:`~.enums.RatelimitWeight`
        How much it 'costs' to load this replay from the api. If the load method
        of the replay makes no api calls, this value is RatelimitWeight.NONE.
        If it makes only light api calls (anything but /api/get_replay),
        this value isRatelimitWeight.LIGHT. If it makes any heavy api calls
        (/api/get_replay), this value is RatelimitWeight.HEAVY.
        See the RatelimitWeight documentation for more details.
    """
    def __init__(self, timestamp, map_id, username, user_id, mods, replay_id, replay_data, detect, weight):
        self.timestamp = timestamp
        self.map_id = map_id
        self.username = username
        self.user_id = user_id
        self.mods = mods
        self.replay_id = replay_id
        self.replay_data = replay_data
        self.detect = detect
        self.weight = weight
        self.loaded = True

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

    def set_cg_options(self, cache, steal_thresh, rx_thresh, detect):
        self.detect = detect if self.detect == config.detect else config.detect

    def __repr__(self):
        return (f"Replay(timestamp={self.timestamp},map_id={self.map_id},user_id={self.user_id},mods={self.mods},detect={self.detect},"
               f"replay_id={self.replay_id},weight={self.weight},loaded={self.loaded},username={self.username})")

    def __str__(self):
        return f"Replay by {self.username} on {self.map_id}"


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
    mods: int
        The bitwise mod combination the replay was played with. If `None`, the
        highest scoring replay of ``user_id`` on ``map_id`` will be loaded,
        regardless of mod combination. Otherwise, the replay with ``mods``
        will be loaded.
    detect: :class:`~.enums.Detect`
        What cheats to run tests to detect.
    cache: bool
        Whether to cache this replay or not.

    Notes
    -----

    """

    def __init__(self, map_id, user_id, mods=None, detect=None, cache=None):
        self.log = logging.getLogger(__name__ + ".ReplayMap")
        self.map_id = map_id
        self.user_id = user_id
        self.mods = mods
        self.detect = detect if detect is not None else config.detect
        self.cache = cache if cache is not None else config.cache
        self.weight = RatelimitWeight.HEAVY
        self.loaded = False

    def load(self, loader):
        """
        Loads the data for this replay from the api.

        Parameters
        ----------
        loader: :class:`~.loader.Loader`
            The :class:`~.loader.Loader` to load this replay with.

        Notes
        -----
        If ``replay.loaded`` is ``True``, this method has no effect.
        ``replay.loaded`` is set to ``True`` after this method loads the replay.
        """
        self.log.debug("Loading %r", self)
        if(self.loaded):
            self.log.debug("%s already loaded, not loading", self)
            return
        info = loader.user_info(self.map_id, user_id=self.user_id, mods=self.mods)
        replay_data = loader.replay_data(info, cache=self.cache)
        Replay.__init__(self, info.timestamp, self.map_id, info.username, self.user_id, info.mods, info.replay_id, replay_data, self.detect, self.weight)
        self.log.log(TRACE, "Finished loading %s", self)

    def cascade_options(self, cache, steal_thresh, rx_thresh, detect):
        self.cache = cache if self.cache == config.cache else self.cache
        self.detect = detect if self.detect == config.detect else self.detect

    def __repr__(self):
        if self.loaded:
            return(f"ReplayMap(timestamp={self.timestamp},map_id={self.map_id},user_id={self.user_id},mods={self.mods},"
                f"detect={self.detect},replay_id={self.replay_id},weight={self.weight},loaded={self.loaded},"
                f"username={self.username})")
        else:
            return (f"ReplayMap(map_id={self.map_id},user_id={self.user_id},mods={self.mods},detect={self.detect},"
                f"weight={self.weight},loaded={self.loaded})")

    def __str__(self):
        return f"{'Loaded' if self.loaded else 'Unloaded'} ReplayMap by {self.user_id} on {self.map_id}"

class ReplayPath(Replay):
    """
    A :class:`~.Replay` saved locally in an ``osr`` file.

    To instantiate a ReplayPath, you only need to know the path to the osr file. Although this class still
    loads some information from the api - like the map id and the user id - no RatelimitWeight.HEAVY calls
    are made, making this a relatively light replay to load. Of course, the replay has to already be downloaded
    to instantiate this class, sometimes making it less than ideal.

    Attributes:
        [String or Path] path: A pathlike object representing the absolute path to the osr file.
        Detect detect: What cheats to run tests to detect.
        Boolean loaded: Whether this replay has been loaded. If True, calls to #load will have no effect.
                        See #load for more information.
        RatelimitWeight weight: RatelimitWeight.LIGHT, as this class' load method makes only light api calls.
                                See RatelimitWeight documentation for more information.
    """

    def __init__(self, path, detect=None, cache=None):
        """
        Initializes a ReplayPath instance.

        Args:
            [String or Path] path: A pathlike object representing the absolute path to the osr file.
            Detect detect: What cheats to run tests to detect.
        """

        self.log = logging.getLogger(__name__ + ".ReplayPath")
        self.path = path
        self.detect = detect if detect is not None else config.detect
        self.cache = cache if cache is not None else config.cache
        self.weight = RatelimitWeight.LIGHT
        self.loaded = False

    def __repr__(self):
        if self.loaded:
            return (f"ReplayPath(path={self.path},map_id={self.map_id},user_id={self.user_id},mods={self.mods},detect={self.detect},"
                    f"replay_id={self.replay_id},weight={self.weight},loaded={self.loaded},username={self.username})")
        else:
            return f"ReplayPath(path={self.path},detect={self.detect},weight={self.weight},loaded={self.loaded})"

    def __str__(self):
        if self.loaded:
            return f"Loaded ReplayPath by {self.username} on {self.map_id} at {self.path}"
        else:
            return f"Unloaded ReplayPath at {self.path}"

    def load(self, loader):
        """
        Loads the data for this replay from the osr file given by the path. See circleparse.parse_replay_file for
        implementation details. This method has no effect if replay.loaded is True.

        The superclass Replay is initialized after this call, setting replay.loaded to True. Multiple
        calls to this method will have no effect beyond the first.
        """

        self.log.debug("Loading ReplayPath %r", self)
        if self.loaded:
            self.log.debug("%s already loaded, not loading", self)
            return

        loaded = circleparse.parse_replay_file(self.path)
        map_id = loader.map_id(loaded.beatmap_hash)
        user_id = loader.user_id(loaded.player_name)

        Replay.__init__(self, loaded.timestamp, map_id, loaded.player_name, user_id, loaded.mod_combination,
                        loaded.replay_id, loaded.play_data, self.detect, self.weight)
        self.log.log(TRACE, "Finished loading %s", self)

    def cascade_options(self, cache, steal_thresh, rx_thresh, detect):
        self.cache = cache if self.cache == config.cache else self.cache
        self.detect = detect if self.detect == config.detect else self.detect
