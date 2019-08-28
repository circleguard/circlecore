import abc
import logging

import circleparse
import numpy as np

from circleguard.enums import Detect, RatelimitWeight
from circleguard import config
from circleguard.utils import TRACE, span_to_list


class Loadable(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def load(self, loader):
        pass

    def filter(self, loader, include):
        return include(self)

class Container(Loadable, abc.ABC):

    def __init__(self, loadables, loadables2=None, cache=None, steal_thresh=None, rx_thresh=None, include=None, detect=None):
        """
        Initializes a Container instance.

        Args:
            List [Loadable] replays: A list of Lodable objects.
            Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
            Integer steal_thresh: If a Comparison scores below this value, it is considered cheated.
                    Defaults to 18, or the config value if changed.
            Integer rx_thresh: if a replay has a ur below this value, it is considered cheated.
                    Deaults to 50, or the config value if changed.
            Function include: A Predicate function that returns True if the replay should be loaded, and False otherwise.
                    The include function will be passed a single argument - the circleguard.Replay object, or one
                    of its subclasses.
            Detect detect: What cheats to run tests to detect. This will only overwrite replay's settings in this Check
                    if the replays were not given a Detect different from the (default) config value.
        """

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
        return self.loadables + self.loadables2

    def load(self, loader):
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
                replays += loadable.all_replays2()
            else:
                replays.append(loadable)
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
    Contains a list of Replay objects (or subclasses thereof) and how to proceed when
    investigating them for cheats.

    Attributes:
        List [Loadable] replays: A list of Loadable objects.
        Integer steal_thresh: If a comparison scores below this value, its Result object has ischeat set to True.
                Defaults to 18, or the config value if changed.
        Integer rx_thresh: if a replay has a ur below this value, it is considered cheated.
                Deaults to 50, or the config value if changed.
        Function include: A Predicate function that returns True if the replay should be loaded, and False otherwise.
                The include function will be passed a single argument - the circleguard.Replay object, or one
                of its subclasses.
        Detect detect: What cheats to run tests to detect.
        Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
        Boolean loaded: False at instantiation, set to True once check#load is called. See check#load for
                more details.
    """

    def __init__(self, loadables, loadables2=None, cache=None, steal_thresh=None, rx_thresh=None, include=None, detect=None):
        """
        Initializes a Check instance.

        Args:
            List [Loadable] replays: A list of Replay or Container objects.
            Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
            Integer steal_thresh: If a Comparison scores below this value, it is considered cheated.
                    Defaults to 18, or the config value if changed.
            Integer rx_thresh: if a replay has a ur below this value, it is considered cheated.
                    Deaults to 50, or the config value if changed.
            Function include: A Predicate function that returns True if the replay should be loaded, and False otherwise.
                    The include function will be passed a single argument - the circleguard.Replay object, or one
                    of its subclasses.
            Detect detect: What cheats to run tests to detect. This will only overwrite replay's settings in this Check
                    if the replays were not given a Detect different from the (default) config value.
        """

        super().__init__(loadables, loadables2, cache, steal_thresh, rx_thresh, include, detect)
        self.cascade_options(self.cache, self.steal_thresh, self.rx_thresh, self.detect)

    def num_replays(self):
        num = 0
        for loadable in self.all_loadables():
            if isinstance(loadable, Container):
                num += loadable.num_replays()
            else:
                num += 1



class Replay(Loadable):
    def __init__(self, timestamp, map_id, username, user_id, mods, replay_id, replay_data, detect, weight):
        """
        Initializes a Replay instance.

        Args:
            Datetime timestamp: When this replay was played.
            Integer map_id: The map id the replay was played on, or 0 if unknown or on an unsubmitted map.
            String username: The username of the player who made the replay.
            Integer user_id: The id of the player who made the replay, or 0 if unknown or a restricted player.
            Integer mods: The mods the replay was played with.
            Integer replay_id: The id of this replay, or 0 if it does not have an id (unsubmitted replays have no id).
            List [circleparse.Replay.ReplayEvent] replay_data: An array containing objects with the attributes x, y, time_since_previous_action,
                            and keys_pressed. If the replay could not be loaded (from the api or otherwise), this field should be None.
                            This means that this replay will not be compared against other replays or investigated for cheats.
            Detect detect: What cheats to run tests to detect.
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
        self.detect = detect
        self.weight = weight
        self.loaded = True

    def __repr__(self):
        return (f"Replay(timestamp={self.timestamp},map_id={self.map_id},user_id={self.user_id},mods={self.mods},detect={self.detect},"
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

    def set_cg_options(self, cache, steal_thresh, rx_thresh, detect):
        self.detect = detect if self.detect == config.detect else config.detect

class ReplayMap(Replay):
    """
    Represents a Replay submitted to online servers, that can be retrieved from the osu api.

    The only things you need to know to instantiate a ReplayMap
    are the user who made the replay, and the map it was made on.

    Attributes:
        Integer map_id: The id of the map the replay was made on.
        Integer user_id: The id of the user who made the replay.
        Integer mods: The mods the replay was played with. None if not set when instantiated and has not been loaded yet -
                      otherwise, set to the mods the replay was made with.
        String username: A readable representation of the user who made the replay. If passed,
                         username will be set to this string. Otherwise, it will be set to the user id.
                         This is so you don't need to know a user's username when creating a ReplayMap, only their id.
                         However, if the username is known (by retrieving it through the api, or other means), it is better
                         to represent the Replay with a player's name than an id. Both username and user_id will
                         obviously still be available to you through the result object after comparison.
        Detect detect: What cheats to run tests to detect.
        Boolean loaded: Whether this replay has been loaded. If True, calls to #load will have no effect.
                        See #load for more information.
        RatelimitWeight weight: RatelimitWeight.HEAVY, as this class' load method makes a heavy api call. See RatelimitWeight
                                documentation for more information.
    """

    def __init__(self, map_id, user_id, mods=None, detect=None, cache=None):
        """
        Initializes a ReplayMap instance.

        Args:
            Integer map_id: The id of the map the replay was made on.
            Integer user_id: The id of the user who made the replay.
            Integer mods: The mods the replay was played with. If this is not set, the top scoring replay of the user on the
                          given map will be loaded. Otherwise, the replay with the given mods will be loaded.
            Detect detect: What cheats to run tests to detect.
            Boolean cache: Whether to cache this replay
        """

        self.log = logging.getLogger(__name__ + ".ReplayMap")
        self.map_id = map_id
        self.user_id = user_id
        self.mods = mods
        self.detect = detect if detect is not None else config.detect
        self.cache = cache if cache is not None else config.cache
        self.weight = RatelimitWeight.HEAVY
        self.loaded = False

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

    def load(self, loader):
        """
        Loads the data for this replay from the api. This method silently returns if replay.loaded is True.

        The superclass Replay is initialized after this call, setting replay.loaded to True. Multiple
        calls to this method will have no effect beyond the first.
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

class ReplayPath(Replay):
    """
    Represents a Replay saved locally.

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
