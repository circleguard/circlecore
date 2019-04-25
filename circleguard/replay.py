import abc
import logging

import osrparse
import numpy as np

from circleguard.detect import Detect
from circleguard import config

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

    def __init__(self, replays, replays2=None, thresh=config.thresh, cache=config.cache):
        """
        Initializes a Check instance.

        If only replays is passed, the replays in that list are compared with themselves. If
        both replays and replays2 are passed, the replays in replays are compared only with the
        replays in replays2. See comparer#compare for a more detailed description.

        Args:
            List [Replay] replays: A list of Replay objects.
            List [Replay] replays2: A list of Replay objects to compare against 'replays' if passed.
            Integer thresh: If a comparison scores below this value, its Result object has ischeat set to True.
                            Defaults to 18, or the config value if changed.
            Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
        """

        self.log = logging.getLogger(__name__ + ".Check")
        self.replays = replays # list of ReplayMap and ReplayPath objects, not yet processed
        self.replays2 = replays2
        self.mode = "double" if replays2 else "single"
        self.loaded = False
        self.thresh = thresh
        self.cache = cache

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

        if(self.loaded):
            return
        for replay in self.replays:
            self.log.debug("Loading replay of type %s", type(replay).__name__)
            replay.load(loader)
        if(self.replays2):
            for replay in self.replays2:
                self.log.debug("Loading replay of type %s from replays2", type(replay).__name__)
                replay.load(loader)
        self.loaded = True
        self.log.debug("Finished loading Check object")


class Replay(abc.ABC):
    def __init__(self, username, mods, replay_id, replay_data, detect, loaded):
        """
        Initializes a Replay instance.
        """

        self.username = username
        self.mods = mods
        self.replay_id = replay_id
        self.replay_data = replay_data
        self.detect = detect
        self.loaded = loaded

    @abc.abstractclassmethod
    def load(self, loader):
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

    def __init__(self, map_id, user_id, mods=None, username=None, detect=Detect.ALL):
        """
        todo documentation

        String username: If passed, username will be set to this string. Otherwise, it will be set to the user id.
                         This is to only require you to know the user id for create a ReplayMap, instead of using extra
                         api requests to retrieve the username. However, if the username is known, it is better to represent
                         the Replay with a player's name than an id. Both username and user_id will obviously still be available
                         to you through the result object after comparison.
        """

        self.log = logging.getLogger(__name__ + ".ReplayMap")
        self.map_id = map_id
        self.user_id = user_id
        self.mods = mods
        self.detect = detect
        self.loaded = False
        self._username = username

    def load(self, loader):
        if(self.loaded):
            self.log.debug("Replay already loaded, not loading")
            return
        info = loader.user_info(self.map_id, user_id=self.user_id, mods=self.mods)
        Replay.__init__(self, self.user_id if not self._username else self._username, info.mods, info.replay_id, loader.replay_data(info), self.detect, loaded=True)


class ReplayPath(Replay):

    def __init__(self, path, detect=Detect.ALL):
        self.log = logging.getLogger(__name__ + ".ReplayPath")
        self.path = path
        self.detect = detect
        self.loaded = False

    def load(self, loader):
        if(self.loaded):
            self.log.debug("Replay already loaded, not loading")
            return
        # no, we don't need loader for ReplayPath, but to reduce type checking when calling we make the method signatures homogeneous
        loaded = osrparse.parse_replay_file(self.path)
        replay_id = loaded.replay_id if loaded.replay_id != 0 else None # if score is 0 it wasn't submitted (?)
        Replay.__init__(self, loaded.player_name, loaded.mod_combination, replay_id, loaded.play_data, self.detect, loaded=True)
