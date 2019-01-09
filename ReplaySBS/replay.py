import math

from config import REPLAY_PORTION

import numpy as np

class Replay:
    def __init__(self, replay_data):
        self.player_name = replay_data.player_name
        self.play_data = replay_data.play_data
        self.average_distance = ""
        
    @staticmethod
    def compute_similarity(user_replay, check_replay):
        players = " ({} vs {})".format(user_replay.player_name, check_replay.player_name)
        
        get_xy = lambda event: (event.x, event.y)
        
        coords_user = np.array(list(map(get_xy, user_replay.play_data)))
        coords_check = np.array(list(map(get_xy, check_replay.play_data)))

        difference = coords_user - coords_check

        distance = (difference ** 2).sum(axis = 1) ** 0.5

        mu = distance.mean()
        sigma = distance.std()
        
        return str(mu) + ", " + str(sigma) + players
 
