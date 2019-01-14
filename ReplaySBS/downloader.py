import requests
from datetime import datetime
import time

import secret
from config import API_SCORES, API_REPLAY


def api(function):
    """
    Decorator that checks if we can refresh the time at which we started our requests because 
    it's been more than RATELIMIT_RESET since the first request of the cycle (see Downloader.reset_loads for more).

    If we've refreshed our ratelimits, sets start_time to be the current datetime.
    """
    def wrapper(*args, **kwargs):
        # check if we've refreshed our ratelimits yet
        difference = datetime.now() - Downloader.start_time
        if(difference.seconds > Downloader.RATELIMIT_RESET):
            Downloader.start_time = datetime.now()
            
        return function.__func__(*args, **kwargs) # then call the function, use __func__ because it's static
    return wrapper


class Downloader():
    """
    This class is not meant to be instantiated, instead only static methods and class variables used.
    This is because we only use one api key for the entire project, and making all methods static provides
    cleaner access than passing around a single Downloader class.

    Manages interactions with the osu api - if the api ratelimits the key we wait until we refresh our ratelimits
    and retry the request.
    """

    RATELIMIT_RESET = 60 # time in seconds until the api refreshes our ratelimits
    start_time = datetime.min # when we started our requests cycle


    def __init__(self):
        """
        This class should never be instantiated. All methods are static.
        """

        raise Exception("This class is not meant to be instantiated. Use the static methods instead")

    @api
    @staticmethod
    def users_from_beatmap(map_id):
        """
        Returns a list of all user ids of the top 50 plays on the given beatmap.
        """
        
        response = requests.get(API_SCORES.format(map_id)).json()
        if(Downloader.check_response(response)):
            Downloader.enforce_ratelimit()
            return Downloader.users_from_beatmap(map_id)

        users = [x["user_id"] for x in response]
        return users
    
    @api
    @staticmethod
    def replay_data(map_id, user_id):
        """
        Queries the api for replay data from the given user on the given map.

        Returns:
            The lzma bytestring returned by the api.
        """
        
        print("Requesting replay by {} on map {}".format(user_id, map_id))
        response = requests.get(API_REPLAY.format(map_id, user_id)).json()
        if(Downloader.check_response(response)):
            Downloader.enforce_ratelimit()
            return Downloader.replay_data(map_id, user_id)

        return response["content"]


    @staticmethod
    def check_response(response):
        """
        Checks the given api response for a ratelimit error.

        Returns:
            True if the key is ratelimited, false otherwise.
        """
        if("error" in response):
            return True
        else:
            return False

    @staticmethod
    def enforce_ratelimit():
        """
        Enforces the ratelimit by sleeping the thread until it's safe to make requests again.
        """

        difference = datetime.now() - Downloader.start_time
        seconds_passed = difference.seconds
        if(seconds_passed > Downloader.RATELIMIT_RESET):
            return

        # sleep the remainder of the reset cycle so we guarantee it's been that long since the first request
        sleep_seconds = Downloader.RATELIMIT_RESET - seconds_passed
        print("Ratelimited. Sleeping for {} seconds".format(sleep_seconds))
        time.sleep(sleep_seconds)
