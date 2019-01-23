import requests
from argparser import argparser
from draw import Draw
import itertools

from loader import Loader
from local_replay import LocalReplay
from online_replay import OnlineReplay
from comparer import Comparer
from investigator import Investigator
from config import PATH_REPLAYS_USER, PATH_REPLAYS_CHECK, WHITELIST

class Anticheat:

    def __init__(self, args):
        """
        Initializes an Anticheat instance.
        """

        self.args = args

    def run(self):
        """
        Starts loading and detecting replays based on the args passed through the command line.
        """

        args = self.args
        if(args.local):
            # get all local user replays (used in every --local case)
            replays1 = [LocalReplay.from_path(osr_path) for osr_path in PATH_REPLAYS_USER]
            if(args.map_id and args.user_id):
                # compare every local replay with just the given user + map replay
                replays2 = [OnlineReplay.from_map(args.map_id, args.user_id, args.cache)]
                comparer = Comparer(args.threshold, replays1, replays2=replays2)
                comparer.compare(mode="double")
                return
            if(args.map_id):
                # compare every local replay with every leaderboard entry
                user_ids = Loader.users_from_beatmap(args.map_id, args.number)
                replays2 = [OnlineReplay.from_map(args.map_id, user_id, args.cache) for user_id in user_ids]
                comparer = Comparer(args.threshold, replays1, replays2=replays2)
                comparer.compare(mode="double")
                return

            else:
                # checks every replay listed in PATH_REPLAYS_USER against every replay listed in PATH_REPLAYS_CHECK
                replays2 = [LocalReplay.from_path(osr_path) for osr_path in PATH_REPLAYS_CHECK]
                comparer = Comparer(args.threshold, replays1, replays2=replays2)
                comparer.compare(mode="double")
                return

        if(args.map_id and args.user_id): # passed both -m and -u but not -l
            replays1 = [OnlineReplay.from_map(args.map_id, args.user_id, args.cache)]
            user_ids = Loader.users_from_beatmap(args.map_id, args.number)
            replays2 = [OnlineReplay.from_map(args.map_id, user_id, args.cache) for user_id in user_ids]
            comparer = Comparer(args.threshold, replays1, replays2=replays2)
            comparer.compare(mode="double")
            return

        if(args.map_id): # only passed -m
            # get all 50 top replays
            replays = [OnlineReplay.from_map(args.map_id, check_id, args.cache) for check_id in Loader.users_from_beatmap(args.map_id, args.number)]
            comparer = Comparer(args.threshold, replays)
            comparer.compare(mode="single")
            return

if __name__ == '__main__':
    anticheat = Anticheat(argparser.parse_args())
    anticheat.run()
