import abc
import logging
from typing import Iterable

import circleparse
import numpy as np

from circleguard.enums import Detect, RatelimitWeight
from circleguard import config
from circleguard.utils import TRACE


class Replay(abc.ABC):
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

    @abc.abstractclassmethod
    def load(self, loader, cache):
        """
        Loads replay data of the replay, from the osu api or from some other source.
        Implementation is up to the specific subclass.

        To meet the specs of this method, subclasses must set replay.loaded to True after this method is called,
        and replay.replay_data must be a valid Replay object, as defined by circleparse.Replay. Both of these specs
        can be met if the superclass circleguard.Replay is initialized in the load method with a valid Replay, as
        circleguard.Replay.__init__ sets replay.loaded to true by default.
        """

        ...


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

    def __init__(self, map_id, user_id, mods=None, detect=None):
        """
        Initializes a ReplayMap instance.

        Args:
            Integer map_id: The id of the map the replay was made on.
            Integer user_id: The id of the user who made the replay.
            Integer mods: The mods the replay was played with. If this is not set, the top scoring replay of the user on the
                          given map will be loaded. Otherwise, the replay with the given mods will be loaded.
            Detect detect: What cheats to run tests to detect.
        """

        self.log = logging.getLogger(__name__ + ".ReplayMap")
        self.map_id = map_id
        self.user_id = user_id
        self.mods = mods
        self.detect = detect if detect is not None else config.detect
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

    def load(self, loader, cache=None):
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
        replay_data = loader.replay_data(info, cache=cache)
        Replay.__init__(self, info.timestamp, self.map_id, info.username, self.user_id, info.mods, info.replay_id, replay_data, self.detect, self.weight)
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
        Detect detect: What cheats to run tests to detect.
        Boolean loaded: Whether this replay has been loaded. If True, calls to #load will have no effect.
                        See #load for more information.
        RatelimitWeight weight: RatelimitWeight.LIGHT, as this class' load method makes only light api calls.
                                See RatelimitWeight documentation for more information.
    """

    def __init__(self, path, detect=None):
        """
        Initializes a ReplayPath instance.

        Args:
            [String or Path] path: A pathlike object representing the absolute path to the osr file.
            Detect detect: What cheats to run tests to detect.
        """

        self.log = logging.getLogger(__name__ + ".ReplayPath")
        self.path = path
        self.detect = detect if detect is not None else config.detect
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

    def load(self, loader, cache=None):
        """
        Loads the data for this replay from the osr file given by the path. See circleparse.parse_replay_file for
        implementation details. This method has no effect if replay.loaded is True.

        The superclass Replay is initialized after this call, setting replay.loaded to True. Multiple
        calls to this method will have no effect beyond the first.

        The cache argument here currently has no effect, and is only added for homogeneity with ReplayMap#load.
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


class Check():
    """
    Contains a list of Replay objects (or subclasses thereof) and how to proceed when
    investigating them for cheats.

    Attributes:
        List [Replay] replays: A list of Replay objects.
        List [Replay] replays2: A list of Replay objects to compare against 'replays' if passed.
        Integer steal_thresh: If a comparison scores below this value, its Result object has ischeat set to True.
                Defaults to 18, or the config value if changed.
        Integer rx_thresh: if a replay has a ur below this value, it is considered cheated.
                Deaults to 50, or the config value if changed.
        Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
        String mode: "single" if only replays was passed, or "double" if both replays and replays2 were passed.
        Boolean loaded: False at instantiation, set to True once check#load is called. See check#load for
                more details.
        Detect detect: What cheats to run tests to detect.
    """

    def __init__(self, replays, replays2=None, cache=None, steal_thresh=None, rx_thresh=None, include=None, detect=None):
        """
        Initializes a Check instance.

        If only replays is passed, the replays in that list are compared with themselves. If
        both replays and replays2 are passed, the replays in replays are compared only with the
        replays in replays2. See comparer#compare for a more detailed description.

        Args:
            List [Replay] replays: A list of Replay objects.
            List [Replay] replays2: A list of Replay objects to compare against 'replays' if passed.
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

        self.log = logging.getLogger(__name__ + ".Check")
        self.replays = replays # list of ReplayMap and ReplayPath objects, not yet processed
        self.replays2 = replays2 if replays2 else [] # make replays2 fake iterable, for #filter mostly
        self.detect = detect if detect else config.detect
        for r in self.all_replays():
            # if detect was not passed to Replays they default to config.detect,
            # we should only overwrite when detect wasn't explicitly passed to
            # the replay
            if r.detect == config.detect:
                r.detect = self.detect
        self.mode = "double" if replays2 else "single"
        self.loaded = False
        self.steal_thresh = steal_thresh if steal_thresh else config.steal_thresh
        self.rx_thresh = rx_thresh if rx_thresh else config.rx_thresh
        self.cache = cache if cache else config.cache
        self.include = include if include else config.include

    def filter(self):
        """
        Filters self.replays and self.replays2 to contain only Replays where self.include returns True
        when the Replay is passed. This gives total control to what replays end up getting loaded
        and compared.
        """

        self.log.info("Filtering replays from Check")
        self.replays = [replay for replay in self.replays if self._include(replay)]
        self.replays2 = [replay for replay in self.replays2 if self._include(replay)]


    def _include(self, replay):
        """
        An internal helper method to create log statements from inside a list comprehension.
        """

        if self.include(replay):
            self.log.log(TRACE, "%r passed include(), keeping in Check replays", replay)
            return True
        else:
            self.log.debug("%r failed include(), filtering from Check replays", replay)
            return False

    def load(self, loader):
        """
        If check.loaded is already true, this method silently returns. Otherwise, loads replay data for every
        replay in both replays and replays2, and sets check.loaded to True. How replays are loaded is up to
        the implementation of the specific subclass of the Replay. Although the subclass may not use the loader
        object, it is still passed regardless to reduce type checking. For implementation details, see the load
        method of each Replay subclass.

        Args:
            Loader loader: The loader to handle api requests, if required by the Replay.
        """

        self.log.info("Loading replays from Check")

        if self.loaded :
            self.log.debug("Check already loaded, not loading individual Replays")
            return
        for replay in self.replays:
            replay.load(loader, self.cache)
        if self.replays2:
            for replay in self.replays2:
                replay.load(loader, self.cache)
        self.loaded = True
        self.log.debug("Finished loading Check object")

    def all_replays(self) -> Iterable[Replay]:
        """
        Convenience method for accessing all replays stored in this object.

        Returns:
            A list of all replays in this Check object (replays1 + replays2)
        """
        return self.replays + self.replays2
