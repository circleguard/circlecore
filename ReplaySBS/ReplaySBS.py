from argparser import argparser
import requests
import itertools

from downloader import Downloader
from replay import Replay
from config import PATH_REPLAYS_USER, PATH_REPLAYS_CHECK, WHITELIST

def main():
    """checks all replays in PATH_REPLAYS_USER against all replays in PATH_REPLAYS_CHECK"""

    args = argparser.parse_args()
    if(args.map_id and args.user_id): # passed both -m and -u
        user_replay = Replay.from_map(args.map_id, args.user_id, args.user_id)

        for check_id in Downloader.users_from_beatmap(args.map_id):
            check_replay = Replay.from_map(args.map_id, check_id, check_id)
            result = Replay.compute_similarity(user_replay, check_replay)
            mean = result[0]
            sigma = result[1]
            players = result[2]
            if(mean < 20):
                print("{:.1f} similarity {}".format(mean, players))
        
        return

    if(args.map_id): # only passed -m
        # get all 50 top replays
        replays = [Replay.from_map(args.map_id, check_id, check_id) for check_id in Downloader.users_from_beatmap(args.map_id)]
        print("comparing all replays (1225 combinations)")
        for replay1, replay2 in itertools.combinations(replays, 2):
            if(replay1.player_name in WHITELIST and replay2.player_name in WHITELIST):
                continue # don't waste time comparing two 100% clean players
                
            result = Replay.compute_similarity(replay1, replay2)
            mean = result[0]
            sigma = result[1]
            players = result[2]
            if(mean < 20):
                print("{:.1f} similarity {}".format(mean, players))
       
        return
        

    # checks every replay listed in PATH_REPLAYS_USER against every replay listed in PATH_REPLAYS_CHECK
    for osr_path in PATH_REPLAYS_USER:
        user_replay = Replay.from_path(osr_path)

        for osr_path2 in PATH_REPLAYS_CHECK:
            check_replay = Replay.from_path(osr_path2)
            print(Replay.compute_similarity(user_replay, check_replay))

if __name__ == '__main__':
    main()
