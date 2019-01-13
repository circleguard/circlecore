import base64
import osrparse
import requests

import numpy as np

from config import API_REPLAY

class Interpolation:
    """A utility class containing coordinate interpolations."""

    @staticmethod
    def linear(x1, x2, r):
        """Linearly interpolates coordinate tuples x1 and x2 with ratio r."""

        return ((1 - r) * x1[0] + r * x2[0], (1 - r) * x1[1] + r * x2[1])

    @staticmethod
    def before(x1, x2, r):
        """Returns the startpoint of the range."""

        return x1

    @staticmethod
    def after(x1, x2, r):
        """Returns the endpoint of the range."""

        return x2

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
        self.length = len(self.play_data)

    @staticmethod
    def compute_similarity(user_replay, check_replay):
        """
        Compare two plays and return their average distance
        and standard deviation of distances.
        """
        players = " ({} vs {})".format(user_replay.player_name, check_replay.player_name)

        # get all coordinates in numpy arrays so that they're arranged like:
        # [ x_1 x_2 ... x_n
        #   y_1 y_2 ... y_n ]
        # indexed by columns first.
        data1 = user_replay.as_list_with_timestamps()
        data2 = check_replay.as_list_with_timestamps()

        (data1, data2) = Replay.interpolate(data1, data2)

        data1 = [d[1:] for d in data1]
        data2 = [d[1:] for d in data2]

        (mu, sigma) = Replay.compute_data_similarity(data1, data2)

        return "mu = {}, sigma = {} {}".format(mu, sigma, players)

    @staticmethod
    def compute_data_similarity(data1, data2):
        """
        Compares two coordinate datasets and returns their average distance
        and standard deviation.
        """
        data1 = np.array(data1)
        data2 = np.array(data2)

        # switch if the second is longer, so that data1 is always the longest.
        if len(data2) > len(data1):
            (data1, data2) = (data2, data1)

        shortest = len(data2)

        distance = data1[:shortest] - data2
        # square all numbers and sum over the second axis (add row 2 to row 1),
        # finally take the square root of each number to get all distances.
        # [ x_1 x_2 ... x_n   => [ x_1 ** 2 ... x_n ** 2
        #   y_1 y_2 ... y_n ] =>   y_1 ** 2 ... y_n ** 2 ]
        # => [ x_1 ** 2 + y_1 ** 2 ... x_n ** 2 + y_n ** 2 ]
        # => [ d_1 ... d_2 ]
        distance = (distance ** 2).sum(axis=1) ** 0.5

        mu, sigma = distance.mean(), distance.std()

        return (mu, sigma)

    @staticmethod
    def interpolate(data1, data2, interpolation=Interpolation.linear):
        """Interpolates the longer of the datas to match the timestamps of the shorter."""

        # if the first timestamp in data2 is before the first in data1 switch
        # so data1 always has some timestamps before data2.
        if data1[0][0] > data2[0][0]:
            (data1, data2) = (data2, data1)

        # get the smallest index of the timestamps after the first timestamp in data2.
        i = next((i for (i, p) in enumerate(data1) if p[0] > data2[0][0]))

        # remove all earlier timestamps, if data1 is longer than data2 keep one more
        # so that the longest always starts before the shorter dataset.
        data1 = data1[i:] if len(data1) < len(data2) else data1[i - 1:]

        if len(data1) > len(data2):
            (data1, data2) = (data2, data1)

        # for each point in data1 interpolate the points around the timestamp in data2.
        j = 0
        inter = []
        clean = []
        for between in data1:
            # keep a clean version with only values that can be interpolated properly.
            clean.append(between)

            # move up to the last timestamp in data2 before the current timestamp.
            while j < len(data2) - 1 and data2[j][0] < between[0]:
                j += 1

            if j == len(data2) - 1:
                break

            before = data2[j]
            after = data2[j + 1]

            # calculate time differences
            # dt1 =  ---2       , data1
            # dt2 = 1-------3   , data2
            dt1 = between[0] - before[0]
            dt2 = after[0] - before[0]

            # skip trying to interpolate to this event
            # if its surrounding events are not set apart in time
            # and replace it with the event before it
            if dt2 == 0:
                inter.append((between[0], *before[1:]))
                continue

            # interpolate the coordinates in data2
            # according to the ratios of the time differences
            x_inter = interpolation(before[1:], after[1:], dt1 / dt2)

            # filter out interpolation artifacts which send outliers even further away
            if abs(x_inter[0]) > 600 or abs(x_inter[1]) > 600:
                inter.append(between)
                continue

            t_inter = between[0]

            inter.append((t_inter, *x_inter))

        return (clean, inter)

    @staticmethod
    def from_map(map_id, user_id, username):
        replay_data_string = requests.get(API_REPLAY.format(map_id, user_id)).json()["content"]
        # convert to bytes so the lzma can be deocded with osrparse
        replay_data_bytes = base64.b64decode(replay_data_string)
        return Replay(osrparse.parse_replay(replay_data_bytes, pure_lzma=True), player_name=username)

    @staticmethod
    def from_path(path):
        return Replay(osrparse.parse_replay_file(path))

    def as_array(self):
        """
        Gets the playdata as a np array with time as the first axis.
        [ x_1 x_2 ... x_n
          y_1 y_2 ... y_n ]
        """

        return np.array([(e.x, e.y) for e in self.play_data])

    def as_list_with_timestamps(self):
        """Gets the playdata as a list of tuples of absolute time, x and y."""

        # get all offsets sum all offsets before it to get all absolute times
        timestamps = np.array([e.time_since_previous_action for e in self.play_data])
        timestamps = timestamps.cumsum()

        # zip timestamps back to data and convert t, x, y to tuples
        txy = [(z[0], z[1].x, z[1].y) for z in zip(timestamps, self.play_data)]
        # sort to ensure time goes forward as you move through the data
        # in case someone decides to make time go backwards anyway
        txy.sort(key=lambda p: p[0])
        return txy

# fail fast
np.seterr(all='raise')
