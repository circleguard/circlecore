from osrparse import parse_replay_file
from argparser import argparser
import requests

from replay import Replay
from config import PATH_REPLAYS_USER, PATH_REPLAYS_CHECK, API_SCORES

def main():
    """checks all replays in PATH_REPLAYS_USER against all replays in PATH_REPLAYS_CHECK"""

    args = argparser.parse_args()
    if(args.map_id):
        if(args.user_id):
            user_replay = Replay.from_map(args.map_id, args.user_id, args.user_id)
        

        for check_id in [x["user_id"] for x in requests.get(API_SCORES).json()]:
            check_replay = Replay.from_map(args.map_id, check_id, args.user_id)
            print(Replay.compute_similarity(user_replay, check_replay))


    # checks every replay listed in PATH_REPLAYS_USER against every replay listed in PATH_REPLAYS_CHECK
    for osr_path in PATH_REPLAYS_USER:
        user_replay = Replay.from_path(osr_path)

        for osr_path2 in PATH_REPLAYS_CHECK:
            check_replay_data = parse_replay_file(osr_path2)
            check_replay = Replay(check_replay_data)

            print(Replay.compute_similarity(user_replay, check_replay))
        

if __name__ == '__main__':
    main()
