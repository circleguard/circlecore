import requests
from datetime import datetime
import time

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

    RATELIMIT = 100 # true ratelimit is 1200 for normal requests but we should keep activity sub 100.
    RATELIMIT_HEAVY = 10 # true replay ratelimit is 10/min
    RATELIMIT_RESET = 60 # time in seconds until the api refreshes our ratelimits
    load = 0  # how many requests we have made in the past ratelimit cycle
    heavy_load = 0 # how many heavy load requests we've made this cycle (For now, only getting replays)
    start_time = datetime.min # when we started our requests cycle


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
        
        Downloader.check_ratelimit()
        url = API_SCORES.format(map_id)
        users = [x["user_id"] for x in requests.get(url).json()]
        Downloader.load += 1
        return users

    @staticmethod
    def replay_data(map_id, user_id):
        """
        Queries the api for replay data from the given user on the given map.

        Returns:
            The lzma bytestring returned by the api.
        """

        Downloader.check_ratelimit()
        lzma = requests.get(API_REPLAY.format(map_id, user_id)).json()["content"]
        Downloader.heavy_load += 1
        return lzma

    @staticmethod
    def check_ratelimit():
        # first check if we've refreshed our ratelimits yet
        difference = datetime.now() - Downloader.start_time
        if(difference.seconds > Downloader.RATELIMIT_RESET):
            Downloader.load = 0
            Downloader.heavy_load = 0
            Downloader.start_time = datetime.now()
            return

        # then if we're going to hit either the normal or the heavy ratelimit, enforce that before we do
        if(Downloader.load + Downloader.heavy_load + 1 == Downloader.RATELIMIT or Downloader.heavy_load + 1 == Downloader.RATELIMIT_HEAVY):
            Downloader.enforce_ratelimit()
            return
    
    @staticmethod
    def enforce_ratelimit():
        difference = datetime.now() - Downloader.start_time
        seconds_passed = difference.seconds
        if(seconds_passed > Downloader.RATELIMIT_RESET):
            return

        # sleep the remainder of the reset cycle so we guarantee it's been that long since the first request
        time.sleep(Downloader.RATELIMIT_RESET - seconds_passed) 
