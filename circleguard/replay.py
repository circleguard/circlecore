import abc
import logging

import circleparse
import numpy as np

from circleguard.enums import Detect, RatelimitWeight
from circleguard import config
from circleguard.utils import TRACE

class Check():
    """
    Contains a list of Replay objects (or subclasses thereof) and how to proceed when
    investigating them for cheats.

    Attributes:
        List [Replay] replays: A list of Replay objects.
        List [Replay] replays2: A list of Replay objects to compare against 'replays' if passed.
        Integer thresh: If a comparison scores below this value, its Result object has ischeat set to True.
                        Defaults to 18, or the config value if changed.
        Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
        String mode: "single" if only replays was passed, or "double" if both replays and replays2 were passed.
        Boolean loaded: False at instantiation, set to True once check#load is called. See check#load for
                        more details.
    """

    def __init__(self, replays, replays2=None, cache=None, thresh=None, include=None):
        """
        Initializes a Check instance.

        If only replays is passed, the replays in that list are compared with themselves. If
        both replays and replays2 are passed, the replays in replays are compared only with the
        replays in replays2. See comparer#compare for a more detailed description.

        Args:
            List [Replay] replays: A list of Replay objects.
            List [Replay] replays2: A list of Replay objects to compare against 'replays' if passed.
            Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
            Integer thresh: If a comparison scores below this value, its Result object has ischeat set to True.
                            Defaults to 18, or the config value if changed.
        """

        self.log = logging.getLogger(__name__ + ".Check")
        self.replays = replays # list of ReplayMap and ReplayPath objects, not yet processed
        self.replays2 = replays2 if replays2 else [] # make replays2 fake iterable, for #filter mostly
        self.mode = "double" if replays2 else "single"
        self.loaded = False
        self.thresh = thresh if thresh else config.thresh
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

        if(self.include(replay)):
            self.log.log(TRACE, "Replay passed include(), keeping in Check replays")
            return True
        else:
            self.log.debug("Replay failed include(), filtering from Check replays")
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

        if(self.loaded):
            self.log.debug("Check already loaded, not loading individual Replays")
            return
        for replay in self.replays:
            replay.load(loader, self.cache)
        if(self.replays2):
            for replay in self.replays2:
                replay.load(loader, self.cache)
        self.loaded = True
        self.log.debug("Finished loading Check object")

    def all_replays(self):
        """
        Convenience method for accessing all replays stored in this object.

        Returns:
            A list of all replays in this Check object (replays1 + replays2)
        """
        return self.replays + self.replays2


class Replay(abc.ABC):
    def __init__(self, username, mods, replay_id, replay_data, detect, weight):
        """
        Initializes a Replay instance.

        Args:
            String username: The username of the player who made the replay. Whether or not this is their true username
                             has no effect - this field is used to represent the player more readably than their id.
            Integer mods: The mods the replay was played with.
            Integer replay_id: The id of this replay, or 0 if it does not have an id (unsubmitted replays have no id)
            circleparse.Replay replay_data: A circleparse Replay containing the replay data for this replay. If the replay data is not available
                                         (from the api or otherwise), this field should be None. This means that this replay will not be
                                         compared against other replays or investigated for cheats.
            Detect detect: The Detect enum (or bitwise combination of enums), indicating what types of cheats this
                           replay should be investigated or compared for.
            RatelimitWeight weight: How much it 'costs' to load this replay from the api. If the load method of the replay makes no api calls,
                             this value is RatelimitWeight.NONE. If it makes only light api calls (anything but get_replay), this value is
                             RatelimitWeight.LIGHT. If it makes any heavy api calls (get_replay), this value is RatelimitWeight.HEAVY.
                             This value is used internally to determine how long the loader class will have to spend loading replays -
                             currently LIGHT and NONE are treated the same, and only HEAVY values are counted towards replays to load. Note
                             that this has no effect on the comparisons or internal program implementation - it only affects log messages
                             internally, and if you access circleguard#loader#total, it modifies that value as well. See Loader#new_session
                             for more details.
        """

        self.username = username
        self.mods = mods
        self.replay_id = replay_id
        self.replay_data = replay_data
        self.detect = detect
        self.weight = weight
        self.loaded = True


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
        Gets the playdata as a list of tuples of absolute time, x and y.

        Returns:
            A list of tuples of (t, x, y).
        """
        # get all offsets sum all offsets before it to get all absolute times
        timestamps = np.array([e.time_since_previous_action for e in self.replay_data])
        timestamps = timestamps.cumsum()

        # zip timestamps back to data and convert t, x, y to tuples
        txy = [[z[0], z[1].x, z[1].y] for z in zip(timestamps, self.replay_data)]
        # sort to ensure time goes forward as you move through the data
        # in case someone decides to make time go backwards anyway
        txy.sort(key=lambda p: p[0])
        return txy


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
        Detect detect: The Detect enum (or bitwise combination of enums), indicating what types of cheats this
                       replay should be investigated or compared for.
        Boolean loaded: Whether this replay has been loaded. If True, calls to #load will have no effect.
                        See #load for more information.
        RatelimitWeight weight: RatelimitWeight.HEAVY, as this class' load method makes a heavy api call. See RatelimitWeight
                                documentation for more information.
    """

    def __init__(self, map_id, user_id, mods=None, username=None, detect=Detect.ALL):
        """
        Initializes a ReplayMap instance.

        Args:
            Integer map_id: The id of the map the replay was made on.
            Integer user_id: The id of the user who made the replay.
            Integer mods: The mods the replay was played with. If this is not set, the top scoring replay of the user on the
                          given map will be loaded. Otherwise, the replay with the given mods will be loaded.
            String username: A readable representation of the user who made the replay. If passed,
                             username will be set to this string. Otherwise, it will be set to the user id.
                             This is so you don't need to know a user's username when creating a ReplayMap, only their id.
                             However, if the username is known (by retrieving it through the api, or other means), it is
                             better to represent the Replay with a player's name than an id. Both username and user_id
                             will obviously still be available to you through the result object after comparison.
            Detect detect: The Detect enum (or bitwise combination of enums), indicating what types of cheats this
                           replay should be investigated or compared for.
        """

        self.log = logging.getLogger(__name__ + ".ReplayMap")
        self.map_id = map_id
        self.user_id = user_id
        self.mods = mods
        self.detect = detect
        self.weight = RatelimitWeight.HEAVY
        self.loaded = False
        self.username = username if username else user_id

    def load(self, loader, cache=None):
        """
        Loads the data for this replay from the api. This method silently returns if replay.loaded is True.

        The superclass Replay is initialized after this call, setting replay.loaded to True. Multiple
        calls to this method will have no effect beyond the first.
        """
        self.log.debug("Loading ReplayMap for user %d on map %d with mods %d", self.user_id, self.map_id, self.mods)
        if(self.loaded):
            self.log.debug("ReplayMap already loaded, not loading")
            return
        info = loader.user_info(self.map_id, user_id=self.user_id, mods=self.mods)
        replay_data = loader.replay_data(info, cache=cache)
        Replay.__init__(self, self.username, info.mods, info.replay_id, replay_data, self.detect, self.weight)
        self.log.log(TRACE, "Finished loading ReplayMap")


class ReplayPath(Replay):
    """
    Represents a Replay saved locally.

    To instantiate a ReplayPath, you only need to know the path to the osr file. This class has significant
    advantages compared to a ReplayMap - the username is immediately available from the replay, instead of requiring
    an extra api call. The time it takes to load the replay is also significantly less – especially if you factor in
    ratelimits – because there is no need to make a request to the api to retrieve the replay data, only read an osr
    file.

    Of course, to reap those benefits, it requires having the replay already downloaded, which isn't always ideal.

    Attributes:
        [String or Path] path: A pathlike object representing the absolute path to the osr file.
        Detect detect: The Detect enum (or bitwise combination of enums), indicating what types of cheats this
                       replay should be investigated or compared for.
        Boolean loaded: Whether this replay has been loaded. If True, calls to #load will have no effect.
                        See #load for more information.
        RatelimitWeight weight: RatelimitWeight.NONE, as this class' load method makes no api calls. See RatelimitWeight
                                documentation for more information.
    """

    def __init__(self, path, detect=Detect.ALL):
        """
        Initializes a ReplayPath instance.

        Args:
            [String or Path] path: A pathlike object representing the absolute path to the osr file.
            Detect detect: The Detect enum (or bitwise combination of enums), indicating what types of cheats this
                           replay should be investigated or compared for.
        """

        self.log = logging.getLogger(__name__ + ".ReplayPath")
        self.path = path
        self.detect = detect
        self.weight = RatelimitWeight.HEAVY
        self.loaded = False

    def load(self, loader, cache=None):
        """
        Loads the data for this replay from the osr file given by the path. See circleparse.parse_replay_file for
        implementation details. This method has no effect if replay.loaded is True.

        The superclass Replay is initialized after this call, setting replay.loaded to True. Multiple
        calls to this method will have no effect beyond the first.

        The cache argument here currently has no effect, and is only added for homogeneity with ReplayMap#load.
        """

        self.log.debug("Loading ReplayPath with path %s", self.path)
        if(self.loaded):
            self.log.debug("ReplayPath already loaded, not loading")
            return
        # no, we don't need loader for ReplayPath, but to reduce type checking when calling we make the method signatures homogeneous
        loaded = circleparse.parse_replay_file(self.path)
        Replay.__init__(self, loaded.player_name, loaded.mod_combination, loaded.replay_id, loaded.play_data, self.detect, self.weight)
        self.log.log(TRACE, "Finished loading ReplayPath")
