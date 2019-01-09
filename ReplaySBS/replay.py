import math

from config import REPLAY_PORTION

class Replay:
    def __init__(self, replay_data):
        self.player_name = replay_data.player_name
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
 