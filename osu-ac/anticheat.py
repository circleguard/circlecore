import pathlib

ROOT_PATH = pathlib.Path(__file__).parent
if(not (ROOT_PATH / "secret.py").is_file()):
    key = input("Please enter your api key below - you can get it from https://osu.ppy.sh/p/api. "
                "This will only ever be stored locally, and is necessary to retrieve replay data.\n")
    with open(ROOT_PATH / "secret.py", mode="x") as secret:
        secret.write("API_KEY = '{}'".format(key))

import sys
import requests
import itertools

from argparser import argparser
from draw import Draw
from loader import Loader
from local_replay import LocalReplay
from online_replay import OnlineReplay
from comparer import Comparer
from investigator import Investigator
from cacher import Cacher
from config import PATH_REPLAYS_USER, PATH_REPLAYS_CHECK, WHITELIST

class Anticheat:

    def __init__(self, args):
        """
        Initializes an Anticheat instance.
        """

        self.args = args
        if(args.map_id):
            self.users_info = Loader.users_info(args.map_id, args.number)
        if(args.user_id and args.map_id):
            user_info = Loader.user_info(args.map_id, args.user_id)
            self.replays_check = [OnlineReplay.from_map(args.map_id, args.user_id, args.cache, user_info[args.user_id])]

    def run(self):
        """
        Starts loading and detecting replays based on the args passed through the command line.
        """

        if(self.args.local):
            self._run_local()
        elif(self.args.map_id):
            self._run_map()
        else:
            print("Please set either --local (-l) or --map (-m)! ")
            sys.exit(1)

    def _run_local(self):

        args = self.args
        # get all local user replays (used in every --local case)
        replays1 = [LocalReplay.from_path(osr_path) for osr_path in PATH_REPLAYS_USER]
        if(args.map_id and args.user_id):
            # compare every local replay with just the given user + map replay
            comparer = Comparer(args.threshold, replays1, replays2=self.replays_check)
            comparer.compare(mode="double")
            return
        if(args.map_id):
            # compare every local replay with every leaderboard entry
            replays2 = [OnlineReplay.from_map(args.map_id, user_id, args.cache, replay_id) for user_id, replay_id in self.users_info]
            comparer = Comparer(args.threshold, replays1, replays2=replays2)
            comparer.compare(mode="double")
            return

        if(args.single):
            # checks every replay listed in PATH_REPLAYS_USER against every other replay there
            comparer = Comparer(args.threshold, replays1)
            comparer.compare(mode="single")
            return
        else:
            # checks every replay listed in PATH_REPLAYS_USER against every replay listed in PATH_REPLAYS_CHECK
            replays2 = [LocalReplay.from_path(osr_path) for osr_path in PATH_REPLAYS_CHECK]
            comparer = Comparer(args.threshold, replays1, replays2=replays2)
            comparer.compare(mode="double")
            return

    def _run_map(self):

        args = self.args
        # if doing anything online, revalidate cache
        Cacher.revalidate(args.map_id, self.users_info)

        if(args.map_id and args.user_id): # passed both -m and -u but not -l
            replays2 = [OnlineReplay.from_map(args.map_id, user_id, args.cache, replay_id) for user_id, replay_id in self.users_info.items()]
            comparer = Comparer(args.threshold, self.replays_check, replays2=replays2)
            comparer.compare(mode="double")
            return

        if(args.map_id): # only passed -m
            # get all 50 top replays
            replays = [OnlineReplay.from_map(args.map_id, user_id, args.cache, replay_id) for user_id, replay_id in self.users_info.items()]
            comparer = Comparer(args.threshold, replays)
            comparer.compare(mode="single")
            return

if __name__ == '__main__':
    anticheat = Anticheat(argparser.parse_args())
    anticheat.run()
