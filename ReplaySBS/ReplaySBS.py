from argparser import argparser
import requests

import downloader
from replay import Replay
from config import PATH_REPLAYS_USER, PATH_REPLAYS_CHECK

def main():
    """checks all replays in PATH_REPLAYS_USER against all replays in PATH_REPLAYS_CHECK"""

    args = argparser.parse_args()
    if(args.map_id):
        if(args.user_id):
            user_replay = Replay.from_map(args.map_id, args.user_id, args.user_id)
        
        for check_id in downloader.users_from_beatmap(args.map_id):
            check_replay = Replay.from_map(args.map_id, check_id, check_id)
            
            data1 = user_replay.as_list_with_timestamps()
            data2 = check_replay.as_list_with_timestamps()

            (data1, data2) = Replay.interpolate(data1, data2)

            data1 = [(d[1], d[2]) for d in data1]
            data2 = [(d[1], d[2]) for d in data2]
        
            print(user_replay.player_name + " vs " + check_replay.player_name)
            print(Replay.compute_data_similarity(data1, data2))

    # checks every replay listed in PATH_REPLAYS_USER against every replay listed in PATH_REPLAYS_CHECK
    for osr_path in PATH_REPLAYS_USER:
        user_replay = Replay.from_path(osr_path)

        for osr_path2 in PATH_REPLAYS_CHECK:
            check_replay = Replay.from_path(osr_path2)

            data1 = user_replay.as_list_with_timestamps()
            data2 = check_replay.as_list_with_timestamps()

            (data1, data2) = Replay.interpolate(data1, data2)

            data1 = [(d[1], d[2]) for d in data1]
            data2 = [(d[1], d[2]) for d in data2]
        
            print(user_replay.player_name + " vs " + check_replay.player_name)
            print(Replay.compute_data_similarity(data1, data2))

if __name__ == '__main__':
    main()
