from argparser import argparser
import requests

from downloader import Downloader
from replay import Replay
from config import PATH_REPLAYS_USER, PATH_REPLAYS_CHECK
from draw import Draw

def main():
    """checks all replays in PATH_REPLAYS_USER against all replays in PATH_REPLAYS_CHECK"""

    args = argparser.parse_args()
    if(args.map_id):
        if(args.user_id):
            user_replay = Replay.from_map(args.map_id, args.user_id, args.user_id)
        else:
            user_replay = Replay.from_path(PATH_REPLAYS_USER[0])

        for check_id in Downloader.users_from_beatmap(args.map_id):
            check_replay = Replay.from_map(args.map_id, check_id, check_id)
            print(Replay.compute_similarity(user_replay, check_replay))

    # checks every replay listed in PATH_REPLAYS_USER against every replay listed in PATH_REPLAYS_CHECK
    for osr_path in PATH_REPLAYS_USER:
        user_replay = Replay.from_path(osr_path)

        for osr_path2 in PATH_REPLAYS_CHECK:
            check_replay = Replay.from_path(osr_path2)
            result = Replay.compute_similarity(user_replay, check_replay)
            print(result)

            mean = result[0]
            sigma = result[1]
            players = result[2]
            if(mean < 20):
                print("Similarity = {:.1f} {}".format(mean, players))
                answer = input("Would you like to see a visualization of both replays? ")
                if answer == 'Yes' or 'yes' or 'y' or 'Y':
                    data1 = user_replay.play_data
                    data2 = check_replay.play_data
                    Draw().draw_replays(data1, data2)
            else:
                print("No stolen replays were found")


if __name__ == '__main__':
    main()
