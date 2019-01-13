import requests

import secret
from config import API_SCORES, API_REPLAY


class Downloader():
    """
    This class is not meant to be instantiated, instead only static methods and class variables used.
    This is because we only use one api key for the entire project, and making all methods static provides
    cleaner access than passing around a single Downloader class.

    Manages interactions with the osu api - keeps track of 
    ratelimits for different types of requests, and self-ratelimits by sleeping the thread.
    """

    def __init__(self):
        """
        This class should never be instantiated. All methods are static.
        """

        raise Exception("This class is not meant to be instantiated. Use the static methods instead")

    @staticmethod
    def users_from_beatmap(map_id):
        """
        Returns a list of all user ids of the top 50 plays on the given beatmap.
        """

        url = API_SCORES.format(map_id)
        return [x["user_id"] for x in requests.get(url).json()]

    @staticmethod
    def replay_data(map_id, user_id):
        """
        Queries the api for replay data from the given user on the given map.

        Returns:
            The lzma bytestring returned by the api.
        """

        return requests.get(API_REPLAY.format(map_id, user_id)).json()["content"]