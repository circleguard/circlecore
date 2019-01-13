import requests

import secret
from config import API_SCORES, API_REPLAY


"""
This module is an attempt at the singelton pattern, with one instance used throughout the project.

Manages interactions with the osu api - keeps track of 
ratelimits for different types of requests, and self-ratelimits by sleeping the thread.
"""


def users_from_beatmap(map_id):
    """
    Returns a list of all user ids of the top 50 plays on the given beatmap.
    """

    url = API_SCORES.format(map_id)
    return [x["user_id"] for x in requests.get(url).json()]

def replay_data(map_id, user_id):
    """
    Queries the api for replay data from the given user on the given map.

    Returns:
        The lzma bytestring returned by the api.
    """

    return requests.get(API_REPLAY.format(map_id, user_id)).json()["content"]