import abc
import logging

import circleparse
import numpy as np

from circleguard.enums import RatelimitWeight, ModCombination
from circleguard.utils import TRACE, span_to_list


class Loadable(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def load(self, loader, cache):
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
    :meth:`~.load_info` is called. They become fully loaded when :meth:`~.load`
    is called (and if this is called when the ReplayContainer is in the first
    state, :meth:`~.load` will load info first, then load the replays.)

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
    Contains a list of Replay objects (or subclasses thereof) and how to proceed when
    investigating them for cheats.

    Attributes:
        List [Loadable] replays: A list of Loadable objects.
        Detect detect: What cheats to run tests to detect.
        Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
        Boolean loaded: False at instantiation, set to True once check#load is called. See check#load for
                more details.
    """

    def __init__(self, loadables, detect, loadables2=None, cache=None):
        """
        Initializes a Check instance.

        Args:
            List [Loadable] replays: A list of Replay or Map objects.
            Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
            Detect detect: What cheats to run tests to detect.
        """

        self.log = logging.getLogger(__name__ + ".Check")
        self.loadables = [loadables] if isinstance(loadables, Loadable) else loadables
        self.loadables2 = [loadables2] if isinstance(loadables2, Loadable) else [] if loadables2 is None else loadables2
        self.cache = cache
        self.detect = detect
        self.loaded = False

    def all_loadables(self):
        return self.loadables + self.loadables2

    def load(self, loader, cache=None):
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




class Replay(Loadable):
    def __init__(self, timestamp, map_id, username, user_id, mods, replay_id, replay_data, weight):
        """
        Initializes a Replay instance.

        Args:
            Datetime timestamp: When this replay was played.
            Integer map_id: The map id the replay was played on, or 0 if unknown or on an unsubmitted map.
            String username: The username of the player who made the replay.
            Integer user_id: The id of the player who made the replay, or 0 if unknown or a restricted player.
            ModCombination mods: The mods the replay was played with.
            Integer replay_id: The id of this replay, or 0 if it does not have an id (unsubmitted replays have no id).
            List [circleparse.Replay.ReplayEvent] replay_data: An array containing objects with the attributes x, y, time_since_previous_action,
                            and keys_pressed. If the replay could not be loaded (from the api or otherwise), this field should be None.
                            This means that this replay will not be compared against other replays or investigated for cheats.
            RatelimitWeight weight: How much it 'costs' to load this replay from the api. If the load method of the replay makes no api calls,
                            this value is RatelimitWeight.NONE. If it makes only light api calls (anything but get_replay), this value is
                            RatelimitWeight.LIGHT. If it makes any heavy api calls (get_replay), this value is RatelimitWeight.HEAVY.
                            See the RatelimitWeight documentation for more details.
            Compare compare: How to compare this replay against other replays.
        """
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
        Gets the playdata as a list of tuples of absolute time, x, y, and pressed keys.

        Returns:
            A list of tuples of (t, x, y, keys).
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
    Represents a Replay submitted to online servers, that can be retrieved from the osu api.

    The only things you need to know to instantiate a ReplayMap
    are the user who made the replay, and the map it was made on.

    Attributes:
        Integer map_id: The id of the map the replay was made on.
        Integer user_id: The id of the user who made the replay.
        ModCombination mods: The mods the replay was played with. None if not set when instantiated and has not been loaded yet -
                      otherwise, set to the mods the replay was made with.
        String username: A readable representation of the user who made the replay. If passed,
                         username will be set to this string. Otherwise, it will be set to the user id.
                         This is so you don't need to know a user's username when creating a ReplayMap, only their id.
                         However, if the username is known (by retrieving it through the api, or other means), it is better
                         to represent the Replay with a player's name than an id. Both username and user_id will
                         obviously still be available to you through the result object after comparison.
        Boolean loaded: Whether this replay has been loaded. If True, calls to #load will have no effect.
                        See #load for more information.
        RatelimitWeight weight: RatelimitWeight.HEAVY, as this class' load method makes a heavy api call. See RatelimitWeight
                                documentation for more information.
    """

    def __init__(self, map_id, user_id, mods=None, cache=None, info=None):
        """
        Initializes a ReplayMap instance.

        Args:
            Integer map_id: The id of the map the replay was made on.
            Integer user_id: The id of the user who made the replay.
            ModCombination mods: The mods the replay was played with. If this is not set, the top scoring replay of the user on the
                          given map will be loaded. Otherwise, the replay with the given mods will be loaded.
            Boolean cache: Whether to cache this replay
            UserInfo info: If passed, will use this info instead of loading a user info from the api. This can speed up the loading
                    of the Replay by reducing the number of calls by one.
        """

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
        Loads the data for this replay from the api. This method silently returns if replay.loaded is True.

        The superclass Replay is initialized after this call, setting replay.loaded to True. Multiple
        calls to this method will have no effect beyond the first.
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
    Represents a Replay saved locally.

    To instantiate a ReplayPath, you only need to know the path to the osr file. Although this class still
    loads some information from the api - like the map id and the user id - no RatelimitWeight.HEAVY calls
    are made, making this a relatively light replay to load. Of course, the replay has to already be downloaded
    to instantiate this class, sometimes making it less than ideal.

    Attributes:
        [String or Path] path: A pathlike object representing the absolute path to the osr file.
        Boolean loaded: Whether this replay has been loaded. If True, calls to #load will have no effect.
                        See #load for more information.
        RatelimitWeight weight: RatelimitWeight.LIGHT, as this class' load method makes only light api calls.
                                See RatelimitWeight documentation for more information.
    """

    def __init__(self, path, cache=None):
        """
        Initializes a ReplayPath instance.

        Args:
            [String or Path] path: A pathlike object representing the absolute path to the osr file.
        """

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
        Loads the data for this replay from the osr file given by the path. See circleparse.parse_replay_file for
        implementation details. This method has no effect if replay.loaded is True.

        The superclass Replay is initialized after this call, setting replay.loaded to True. Multiple
        calls to this method will have no effect beyond the first.
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
