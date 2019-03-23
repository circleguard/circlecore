from pathlib import Path

import sys
import itertools
import os
from os.path import isfile, join

from circleguard.draw import Draw
from circleguard.loader import Loader
from circleguard.comparer import Comparer
from circleguard.investigator import Investigator
from circleguard.cacher import Cacher
from circleguard.screener import Screener
from circleguard import config
from circleguard.utils import mod_to_int
from circleguard.exceptions import InvalidArgumentsException, CircleguardException
from circleguard.replay import Check, ReplayMap, ReplayPath

class Circleguard:

    def __init__(self, key, replays_path, db_path):
        """
        Initializes a Circleguard instance.

        Args:
            String key: An osu API key
            [Path or String] replays_path: A pathlike object to the directory containing osr files
            [Path or String] db_path: A pathlike object to the databse file to write and/or read cached replays
        """

        self.replays_path = Path(replays_path) # no effect if passed path, but converts string to path
        self.db_path = Path(db_path)
        cacher = Cacher(config.cache, self.db_path)
        self.loader = Loader(cacher, key)

    def run(self, check):
        """
        Compares replays contained in the check object for replay steals.

        Args:
            Check check: A Check object containing either one or two sets of replays. If it was initialized with
                         a single replay set, all replays in that set are compared with each other. If it was
                         initialized with two replay sets, all replays in the first set are compared with all
                         replays in the second set.
        """

        replay_maps = [replay for replay in check.replays if isinstance(replay, ReplayMap)]
        self.loader.new_session(len(replay_maps))
        if(not check.loaded):
            check.load(self.loader) # all replays now have replay data, this is where ratelimit waiting would occur
        comparer = Comparer(check.thresh, check.silent, check.replays, replays2=check.replays2)
        yield from comparer.compare(mode=check.mode)


    def map_check(self, map_id, u=None, num=config.num, cache=config.cache):
        """
        Checks a map's leaderboard for replay steals.

        Args:
            Integer map_id: The id of the map (not the id of the mapset!) to compare replays from.
            Integer u: A user id. If passed, only the replay made by this user id on the given map will be
                       compared with the rest of the lederboard of the map. No other comparisons will be made.
            Integer num: The number of replays to compare from the map. Defaults to 50, or the config value if changed.
                         Loads from the top ranks of the leaderboard, so num=20 will compare the top 20 scores. This
                          number must be between 1 and 100, as restricted by the osu api.
            Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
        """

        replays2 = None
        if(u):
            info = self.loader.user_info(map_id, user_id=u)
            replays2 = [ReplayMap(info.map_id, info.user_id, info.mods)]
        infos = self.loader.user_info(map_id, num=num)
        replays = [ReplayMap(info.map_id, info.user_id, info.mods) for info in infos]
        check = Check(replays, replays2=replays2)
        yield from self.run(check)

    def verify(self, map_id, u1, u2, cache=config.cache):
        """
        Verifies that two user's replay on a map are steals of each other.

        Args:
            Integer map_id: The id of the map to compare replays from.
            Integer u1: The user id of one of the users who set a replay on this map.
            Integer u2: The user id of the second user who set a replay on this map.
            Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
        """

        info1 = self.loader.user_info(map_id, user_id=u1)
        info2 = self.loader.user_info(map_id, user_id=u2)
        replay1 = ReplayMap(info1.map_id, info1.user_id, info1.mods)
        replay2 = ReplayMap(info2.map_id, info2.user_id, info2.mods)

        check = Check([replay1, replay2])
        yield from self.run(check)

    def user_check(self, user_id, num):
        ...

    def local_check(self):
        """
        Compares locally stored osr files for replay steals.
        """

        folder = self.replays_path
        paths = [folder / f for f in os.listdir(folder) if isfile(folder / f) and f != ".DS_Store"]
        replays = [ReplayPath(path) for path in paths]
        check = Check(replays)
        yield from self.run(check)


def set_options(thresh=None, num=None, silent=None, cache=None, failfast=None):
    """
    Changes the default value for different options in circleguard.

    Args:
        Integer thresh: If a comparison scores below this value, its Result object has ischeat set to True. 18 by default.
        Integer num: How many replays to load from a map when doing a map check. 50 by default.
        Boolean cache: Whether downloaded replays should be cached or not. False by default.
        Boolean failfast: Will throw an exception if no comparisons can be made for a given Check object,
                          or silently make no comparisons otherwise. False by default.
    """

    for k,v in locals().items():
        if(not v):
            continue
        if(hasattr(config, k)):
            setattr(config, k, v)
        else: # this only happens if we fucked up, not the user's fault
            raise CircleguardException(f"The key {k} (with value {v}) is not available as a config option")
