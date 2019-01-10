import difflib
import math
import json

from osrparse import parse_replay_file

from replay import Replay
from config import PATH_REPLAYS_USER, PATH_REPLAYS_CHECK

def main():
    # checks every replay listed in PATH_REPLAYS_USER against every replay listed in PATH_REPLAYS_CHECK
    for osr_path in PATH_REPLAYS_USER:
        user_replay_data = parse_replay_file(osr_path)
        user_replay = Replay(user_replay_data)

        for osr_path in PATH_REPLAYS_CHECK:
            check_replay_data = parse_replay_file(osr_path)
            check_replay = Replay(check_replay_data)

            print(Replay.compute_similarity(user_replay, check_replay))
        

if __name__ == '__main__':
    main()
