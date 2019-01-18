import requests
from argparser import argparser
from draw import Draw
import itertools

from downloader import Downloader
from replay import Replay
from config import PATH_REPLAYS_USER, PATH_REPLAYS_CHECK, WHITELIST

args = argparser.parse_args()

def main():
    """
    Checks certain replays against certain others depending on what flags were set.
    """
    
    # keep this otherwise the animation gets garbage collected
    global animation

    if(args.local):
        if(args.map_id and args.user_id):
             # compare every local replay with just the given user + map replay
            replay2 = Replay.from_map(args.map_id, args.user_id)
            for osr_path in PATH_REPLAYS_USER:
                replay1 = Replay.from_path(osr_path)
                compare_replays(replay1, replay2)
            return
        if(args.map_id):
            # compare every local replay with every leaderboard entry
            replays = [Replay.from_path(path) for path in PATH_REPLAYS_USER]
            compare_replays_against_leaderboard(replays, args.map_id)
            return

        else:
            # checks every replay listed in PATH_REPLAYS_USER against every replay listed in PATH_REPLAYS_CHECK
            for osr_path in PATH_REPLAYS_USER:
                user_replay = Replay.from_path(osr_path)

                for osr_path2 in PATH_REPLAYS_CHECK:
                    check_replay = Replay.from_path(osr_path2)
                    compare_replays(user_replay, check_replay)
            return

    if(args.map_id and args.user_id): # passed both -m and -u but not -l
        user_replay = Replay.from_map(args.map_id, args.user_id)

        for check_id in Downloader.users_from_beatmap(args.map_id, args.number):
            check_replay = Replay.from_map(args.map_id, check_id)
            compare_replays(user_replay, check_replay)
        
        return

    if(args.map_id): # only passed -m
        # get all 50 top replays
        replays = [Replay.from_map(args.map_id, check_id) for check_id in Downloader.users_from_beatmap(args.map_id, args.number)]
        print("comparing all replays (1225 combinations)")
        for replay1, replay2 in itertools.combinations(replays, 2):
            if(replay1.player_name in WHITELIST and replay2.player_name in WHITELIST):
                continue # don't waste time comparing two 100% clean players

            compare_replays(replay1, replay2)
        return

def compare_replays_against_leaderboard(local_replays, map_id):
    user_ids = Downloader.users_from_beatmap(args.map_id, args.number)
    # from_map is ratelimited heavily so make sure to only do this operation once, then filter later
    beatmap_replays = [Replay.from_map(map_id, user_id) for user_id in user_ids]
    for local_replay in local_replays:
        # get rid of the user we're checking if they exist (will return ~0 similarity)
        _beatmap_replays = [replay for replay in beatmap_replays if replay.player_name != local_replay.player_name]
        for beatmap_replay in _beatmap_replays:
            compare_replays(local_replay, beatmap_replay)

def compare_replays(replay1, replay2):
    result = Replay.compute_similarity(replay1, replay2)
    mean = result[0]
    # sigma = result[1]
    players = result[2]
    
    if(mean < args.threshold):
        print("{:.1f} similarity {}".format(mean, players))
        
        answer = input("Would you like to see a visualization of both replays? ")
        if answer[0].lower() == "y":
            animation = Draw.draw_replays(user_replay, check_replay)
 
if __name__ == '__main__':
    main()
