import math
import requests
import base64

import osrparse

from config import REPLAY_PORTION, API_REPLAY

class Replay:
    def __init__(self, replay_data, player_name=None):
        # player_name is only passed if we parse the data straight from lzma which does not include username
        # so we provide it manually from get_scores
        self.player_name = replay_data.player_name if player_name is None else player_name 
        self.play_data = replay_data.play_data
        self.average_distance = ""
        
    @staticmethod
    def compute_similarity(user_replay, check_replay):
        coords_user = []
        coords_check = []


        players = " ({} vs {})".format(user_replay.player_name, check_replay.player_name)
        
        user_replay_data = user_replay.play_data
        check_replay_data = check_replay.play_data

        for data in user_replay_data:
            coords_user.append((data.x, data.y))
        for data in check_replay_data:
            coords_check.append((data.x, data.y))

        coords = list(zip(coords_user, coords_check))

        distance_total = 0
        length = int(len(coords) * REPLAY_PORTION)
        for user, check in coords[0:length]:
            x1 = user[0]
            x2 = check[0]
            y1 = user[1]
            y2 = check[1]

            distance = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            distance_total += distance

            
        distance_average = (distance_total/length)

        return str(distance_average) + players
 
    @staticmethod
    def from_map(map_id, user_id, username):
        replay_data_string = requests.get(API_REPLAY.format(map_id, user_id)).json()["content"]
        # convert to bytes so the lzma can be deocded with osrparse
        replay_data_bytes = base64.b64decode(replay_data_string)
        return Replay(osrparse.parse_replay(replay_data_bytes, pure_lzma=True), player_name=username)

    @staticmethod
    def from_path(path):
        return Replay(osrparse.parse_replay_file(path))