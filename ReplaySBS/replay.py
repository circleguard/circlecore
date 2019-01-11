import numpy as np
import math
import requests
import base64

import osrparse

from config import API_REPLAY

class Replay:
    """This class represents a replay as its cursor positions and playername."""
    def __init__(self, replay_data, player_name=None):
        # player_name is only passed if we parse the data straight from lzma which does not include username
        # so we provide it manually from get_scores
        self.player_name = replay_data.player_name if player_name is None else player_name 

        # play_data takes the shape of a list of ReplayEvents
        # with fields x, y, keys_pressed and time_since_previous_action
        self.play_data = replay_data.play_data
        self.average_distance = ""

    @staticmethod
    def compute_similarity(user_replay, check_replay):
        """Compare two plays and return their average distance
        and standard deviation of distances.
        """
        players = " ({} vs {})".format(user_replay.player_name, check_replay.player_name)

        get_xy = lambda event: (event.x, event.y)

        # get all coordinates in numpy arrays so that they're arranged like:
        # [ x_1 x_2 ... x_n
        #   y_1 y_2 ... y_n ]
        # indexed by columns first.
        coords1 = np.array(list(map(get_xy, user_replay.play_data)))
        coords2 = np.array(list(map(get_xy, check_replay.play_data)))

        # switch if the second is longer, so that coords1 is always the longest.
        if len(coords2) > len(coords1):
            (coords1, coords2) = (coords2, coords1)
            
        shortest = len(coords2)
        difference = len(coords1) - len(coords2)

        stats = []
        for offset in range(difference):
            # offset coords1 and calculate the distance for all sets of coordinates.
            distance = coords1[offset:shortest + offset] - coords2

            # square all numbers and sum over the second axis (add row 2 to row 1),
            # finally take the square root of each number to get all distances.
            # [ x_1 x_2 ... x_n   => [ x_1 ** 2 ... x_n ** 2 
            #   y_1 y_2 ... y_n ] =>   y_1 ** 2 ... y_n ** 2 ]
            # => [ x_1 ** 2 + y_1 ** 2 ... x_n ** 2 + y_n ** 2 ]
            # => [ d_1 ... d_2 ]
            distance = (distance ** 2).sum(axis=1) ** 0.5

            # throw a tuple of the average and variance of distances on the list.
            stats.append((distance.mean(), distance.std()))

        # get the statistics of the offset with the smallest average distance.
        stats.sort(key=lambda stat: stat[0])

        (mu, sigma) = stats[0]

        return str(mu) + ", " + str(sigma) + players

 
    @staticmethod
    def from_map(map_id, user_id, username):
        replay_data_string = requests.get(API_REPLAY.format(map_id, user_id)).json()["content"]
        # convert to bytes so the lzma can be deocded with osrparse
        replay_data_bytes = base64.b64decode(replay_data_string)
        return Replay(osrparse.parse_replay(replay_data_bytes, pure_lzma=True), player_name=username)

    @staticmethod
    def from_path(path):
        return Replay(osrparse.parse_replay_file(path))
