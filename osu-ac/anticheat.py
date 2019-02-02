import pathlib

ROOT_PATH = pathlib.Path(__file__).parent
if(not (ROOT_PATH / "secret.py").is_file()):
    key = input("Please enter your api key below - you can get it from https://osu.ppy.sh/p/api. "
                "This will only ever be stored locally, and is necessary to retrieve replay data.\n")
    with open(ROOT_PATH / "secret.py", mode="x") as secret:
        secret.write("API_KEY = '{}'".format(key))

import sys
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

        [SimpleNamespace or argparse.Namespace] args:
            A namespace-like object representing how and what to compare. An example may look like
            `Namespace(cache=False, local=False, map_id=None, number=50, threshold=20, user_id=None)`
        """

        self.cacher = Cacher(args.cache)
        self.args = args
        if(args.map_id):
            self.users_info = Loader.users_info(args.map_id, args.number)
        if(args.user_id and args.map_id):
            user_info = Loader.user_info(args.map_id, args.user_id)[args.user_id] # should be guaranteed to only be a single mapping of user_id to a list
            self.replays_check = [OnlineReplay.from_map(self.cacher, args.map_id, args.user_id, user_info[0], user_info[1], user_info[2])]

    def run(self):
        """
        Starts loading and detecting replays based on the args passed through the command line.
        """
        if(self.args.verify):
            self._run_verify()
        elif(self.args.local):
            self._run_local()
        elif(self.args.map_id):
            self._run_map()
        else:
            print("Please set either --local (-l) or --map (-m)! ")
            sys.exit(1)

    def _run_verify(self):
        args = self.args

        map_id = self.args.verify[0]
        user1_id = self.args.verify[1]
        user2_id = self.args.verify[2]

        user1_info = Loader.user_info(map_id, user1_id)
        user2_info = Loader.user_info(map_id, user2_id)
        replay1 = OnlineReplay.from_user_info(self.cacher, map_id, user1_info)
        replay2 = OnlineReplay.from_user_info(self.cacher, map_id, user2_info)

        comparer = Comparer(args.threshold, args.silent, replay1, replays2=replay2)
        comparer.compare(mode="double")

    def _run_local(self):

        args = self.args
        # get all local user replays (used in every --local case)
        replays1 = [LocalReplay.from_path(osr_path) for osr_path in PATH_REPLAYS_USER]

        threshold = args.threshold
        stddevs = args.stddevs

        if(args.map_id and args.user_id):
            # compare every local replay with just the given user + map replay
            comparer = Comparer(threshold, args.silent, replays1, replays2=self.replays_check, stddevs=stddevs)
            comparer.compare(mode="double")
            return
        if(args.map_id):
            # compare every local replay with every leaderboard entry
            replays2 = OnlineReplay.from_user_info(self.cacher, args.map_id, self.users_info)
            comparer = Comparer(threshold, args.silent, replays1, replays2=replays2, stddevs=stddevs)
            comparer.compare(mode="double")
            return

        if(args.single):
            # checks every replay listed in PATH_REPLAYS_USER against every other replay there
            comparer = Comparer(threshold, args.silent, replays1)
            comparer.compare(mode="single")
            return
        else:
            # checks every replay listed in PATH_REPLAYS_USER against every replay listed in PATH_REPLAYS_CHECK
            replays2 = [LocalReplay.from_path(osr_path) for osr_path in PATH_REPLAYS_CHECK]
            comparer = Comparer(threshold, args.silent, replays1, replays2=replays2, stddevs=stddevs)
            comparer.compare(mode="double")
            return

    def _run_map(self):

        args = self.args

        threshold = args.threshold
        stddevs = args.stddevs

        # if doing anything online, revalidate cache
        self.cacher.revalidate(args.map_id, self.users_info)

        if(args.map_id and args.user_id): # passed both -m and -u but not -l
            replays2 = OnlineReplay.from_user_info(self.cacher, args.map_id, self.users_info)
            comparer = Comparer(threshold, args.silent, self.replays_check, replays2=replays2, stddevs=stddevs)
            comparer.compare(mode="double")
            return

        if(args.map_id): # only passed -m
            # get all 50 top replays
            replays = OnlineReplay.from_user_info(self.cacher, args.map_id, self.users_info)
            comparer = Comparer(threshold, args.silent, replays, stddevs=stddevs)
            comparer.compare(mode="single")
            return

if __name__ == '__main__':
    anticheat = Anticheat(argparser.parse_args())
    anticheat.run()
