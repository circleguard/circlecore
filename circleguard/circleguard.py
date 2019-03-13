from pathlib import Path

import sys
import itertools
import os
from os.path import isfile, join

from circleguard.draw import Draw
from circleguard.loader import Loader
from circleguard.local_replay import LocalReplay
from circleguard.online_replay import OnlineReplay
from circleguard.comparer import Comparer
from circleguard.investigator import Investigator
from circleguard.cacher import Cacher
from circleguard.screener import Screener
from circleguard import config
from circleguard.utils import mod_to_int
from circleguard.exceptions import InvalidArgumentsException
from circleguard.check_types import MapCheck, VerifyCheck, UsersAgainstMap

class Circleguard:

    def __init__(self, key, path):
        """
        Initializes a Circleguard instance.

        String key: An osu API key
        [Path or String] path: A pathlike object representing the absolute path to the directory which contains the database and and replay files.
        """
        path = Path(path) # no effect if passed path, but converts string to path
        # get all replays in path to check against. Load this per circleguard instance or users moving files around while the gui is open
        # results in unintended behavior (their changes not being applied to a new run)
        local_replay_paths = [path / "replays" / f for f in os.listdir(path / "replays") if isfile(path / "replays" / f) and f != ".DS_Store"]
        self.local_replays = [LocalReplay.from_path(osr_path) for osr_path in local_replay_paths]

        self.loader = Loader(key)
        self.cacher = Cacher(config.cache, path / "db" / "cache.db")

    def run(self, check):
        """
        Starts loading and detecting replays based on the args passed through the command line.
        """
        if(isinstance(check, MapCheck)):
            self.loader.new_session(check.num)
            self._run_map(check)
        elif(isinstance(check, VerifyCheck)):
            self._run_verify(check)
        elif(self.args.local):
            self._run_local()
        elif(self.args.map_id):
            self._run_map()
        elif(self.args.user_id):
            self._run_user()
        else:
            print("Please set either --local (-l), --map (-m), --user (-u), or --verify (-v)! ")

    def _run_verify(self, check):
        loader = self.loader
        map_id = check.map_id

        user_info = loader.user_info(map_id, user_id=check.user_id)
        user2_info = loader.user_info(map_id, user_id=check.user2_id)
        replay = loader.replay_from_user_info(self.cacher, user_info)
        replay2 = loader.replay_from_user_info(self.cacher, user2_info)

        comparer = Comparer(check.threshold, check.silent, replay, replays2=replay2, stddevs=check.stddevs)
        comparer.compare(mode="double")

    def _run_local(self):

        args = self.args
        threshold = args.threshold
        stddevs = args.stddevs

        if(args.map_id and args.user_id):
            # compare every local replay with just the given user + map replay
            comparer = Comparer(threshold, args.silent, self.local_replays, replays2=self.replays_check, stddevs=stddevs)
            comparer.compare(mode="double")
            return
        if(args.map_id):
            # compare every local replay with every leaderboard entry (multiple times for different mod sets)
            for user_info in self.user_infos:
                replays2 = self.loader.replay_from_user_info(self.cacher, user_info)
                comparer = Comparer(threshold, args.silent, self.local_replays, replays2=replays2, stddevs=stddevs)
                comparer.compare(mode="double")

            return
        else:
            comparer = Comparer(threshold, args.silent, self.local_replays, stddevs=stddevs)
            comparer.compare(mode="single")

    def _run_map(self, check):
        self.user_infos = [self.loader.user_info(check.map_id, num=check.num, mods=mods) for mods in check.mods]
        threshold = check.threshold
        stddevs = check.stddevs

        # if doing anything online, revalidate cache for all set mods
        for user_info in self.user_infos:
            self.cacher.revalidate(self.loader, user_info)

        if(type(check) is UsersAgainstMap):
            for user_info in self.user_infos:
                replays2 = self.loader.replay_from_user_info(self.cacher, user_info)
                replays2 = [replay for replay in replays2 if replay.replay_id not in [replay.replay_id for replay in self.replays_check]]
                comparer = Comparer(threshold, check.silent, self.replays_check, replays2=replays2, stddevs=stddevs)
                comparer.compare(mode="double")
            return

        if(type(check) is MapCheck): # if it gets here this is always true
            for user_info in self.user_infos:
                replays = self.loader.replay_from_user_info(self.cacher, user_info)
                comparer = Comparer(threshold, check.silent, replays, stddevs=stddevs)
                comparer.compare(mode="single")
            return

    def _run_user(self):
        args = self.args
        screener = Screener(self.cacher, self.loader, args.threshold, args.silent, args.user_id, args.number, args.stddevs)
        screener.screen()


def set_options(thresh=None, num=None, silent=None, cache=None):
    """
    Sets default options for newly created instances of circleguard, and for new runs of existing instances
    """
    for k,v in locals().items():
        if(v and hasattr(config, k)): # if they passed a value and it exists in the config
            setattr(config, k, v)
