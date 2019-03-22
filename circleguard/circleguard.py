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

        String key: An osu API key
        [Path or String] path: A pathlike object representing the absolute path to the directory which contains the database and and replay files.
        """
        self.replays_path = Path(replays_path) # no effect if passed path, but converts string to path
        self.db_path = Path(db_path)
        self.cacher = Cacher(config.cache, self.db_path)
        self.loader = Loader(self.cacher, key)

    def run(self, check):
        """
        Starts loading and detecting replays based on the args passed through the command line.
        """
        replay_maps = [replay for replay in check.replays if isinstance(replay, ReplayMap)]
        self.loader.new_session(len(replay_maps))
        if(not check.loaded):
            check.load(self.loader) # all replays now have replay data, this is where ratelimit waiting would occur
        comparer = Comparer(check.thresh, check.silent, check.replays, replays2=check.replays2)
        yield from comparer.compare(mode=check.mode)


    def map_check(self, map_id, u=None, num=config.num, cache=config.cache):
        replays2 = None
        if(u):
            info = self.loader.user_info(map_id, user_id=u)
            replays2 = [ReplayMap(info.map_id, info.user_id, info.mods)]
        infos = self.loader.user_info(map_id, num=num)
        replays = [ReplayMap(info.map_id, info.user_id, info.mods) for info in infos]
        check = Check(replays, replays2=replays2)
        yield from self.run(check)

    def verify(self, map_id, user1, user2, cache):
        info1 = self.loader.user_info(map_id, user_id=user1)
        info2 = self.loader.user_info(map_id, user_id=user2)
        replay1 = ReplayMap(info1.map_id, info1.user_id, info1.mods)
        replay2 = ReplayMap(info2.map_id, info2.user_id, info2.mods)

        check = Check([replay1, replay2])
        yield from self.run(check)

    def user_check(self, user_id, num):
        ...

    def local_check(self):
        folder = self.replays_path
        paths = [folder / f for f in os.listdir(folder) if isfile(folder / f) and f != ".DS_Store"]
        replays = [ReplayPath(path) for path in paths]
        check = Check(replays)
        yield from self.run(check)


def set_options(thresh=None, num=None, silent=None, cache=None, failfast=None):
    """
    Sets default options for newly created instances of circleguard, and for new runs of existing instances
    """
    for k,v in locals().items():
        if(not v):
            continue
        if(hasattr(config, k)):
            setattr(config, k, v)
        else: # this only happens if we fucked up, not the user's fault
            raise CircleguardException(f"The key {k} (with value {v}) is not available as a config option")
