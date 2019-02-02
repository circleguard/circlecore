import requests
from datetime import datetime
import time
import base64

from enums import Error
from config import API_SCORES_ALL, API_SCORES_USER, API_REPLAY


def api(function):
    """
    Decorator that checks if we can refresh the time at which we started our requests because
    it's been more than RATELIMIT_RESET since the first request of the cycle.

    If we've refreshed our ratelimits, sets start_time to be the current datetime.
    """
    def wrapper(*args, **kwargs):
        # check if we've refreshed our ratelimits yet
        difference = datetime.now() - Loader.start_time
        if(difference.seconds > Loader.RATELIMIT_RESET):
            Loader.start_time = datetime.now()

        return function(*args, **kwargs)
    return wrapper


class Loader():
    """
    Manages interactions with the osu api - if the api ratelimits the key we wait until we refresh our ratelimits
    and retry the request.

    This class is not meant to be instantiated, instead only static methods and class variables used.
    This is because we only use one api key for the entire project, and making all methods static provides
    cleaner access than passing around a single Loader class.
    """

    RATELIMIT_RESET = 60 # time in seconds until the api refreshes our ratelimits
    start_time = datetime.min # when we started our requests cycle


    def __init__(self):
        """
        This class should never be instantiated. All methods are static.
        """

        raise Exception("This class is not meant to be instantiated. Use the static methods instead.")

    @staticmethod
    @api
    def users_info(map_id, num=50):
        """
        Returns a dict mapping each user_id to a list containing [username, replay_id, enabled mods]
        for the top given number of replays on the given map.

        EX: {"1234567": ["tybug", "295871732", 15]} # numbers may not be accurate to true mod bits or user ids

        Args:
            String map_id: The map id to get a list of users from.
            Integer num: The number of ids to fetch. Defaults to 50.
        """

        if(num > 100 or num < 2):
            raise Exception("The number of top plays to fetch must be between 1 and 100 inclusive!")
        response = requests.get(API_SCORES_ALL.format(map_id, num)).json()
        if(Loader.check_response(response)):
            Loader.enforce_ratelimit()
            return Loader.users_info(map_id, num=num)

        info = {x["user_id"]: [x["username"], x["score_id"], int(x["enabled_mods"])] for x in response} # map user id to username, score id and mod bit
        return info

    @staticmethod
    @api
    def user_info(map_id, user_id):
        """
        Returns a dict mapping a user_id to a list containing their [username, replay_id, enabled mods] on a given map.

        Args:
            String map_id: The map id to get the replay_id from.
            String user_id: The user id to get the replay_id from.
        """

        response = requests.get(API_SCORES_USER.format(map_id, user_id)).json()
        if(Loader.check_response(response)):
            Loader.enforce_ratelimit()
            return Loader.user_info(map_id, user_id)
        info = {x["user_id"]: [x["username"], x["score_id"], int(x["enabled_mods"])] for x in response} # map user id to username, score id and mod bit,
                                                                                                        # should only be one response
        return info

    @staticmethod
    @api
    def replay_data(map_id, user_id):
        """
        Queries the api for replay data from the given user on the given map.

        Args:
            String map_id: The map id to get the replay off of.
            String user_id: The user id to get the replay of.

        Returns:
            The lzma bytes (b64 decoded response) returned by the api, or None if the replay was not available.

        Raises:
            Exception if the api response with an error we don't know.
        """

        print("Requesting replay by {} on map {}".format(user_id, map_id))
        response = requests.get(API_REPLAY.format(map_id, user_id)).json()

        error = Loader.check_response(response)
        if(error == Error.NO_REPLAY):
            print("Could not find any replay data for user {} on map {}, skipping".format(user_id, map_id))
            return None
        elif(error == Error.RETRIEVAL_FAILED):
            print("Replay retrieval failed for user {} on map {}, skipping".format(user_id, map_id))
            return None
        elif(error == Error.RATELIMITED):
            Loader.enforce_ratelimit()
            return Loader.replay_data(map_id, user_id)
        elif(error == Error.UNKOWN):
            raise Exception("unkown error when requesting replay by {} on map {}. Please lodge an issue with the devs immediately".format(user_id, map_id))


        return base64.b64decode(response["content"])


    @staticmethod
    def check_response(response):
        """
        Checks the given api response for a ratelimit error.

        Args:
            String response: The api-returned response to check.

        Returns:
            An Error enum corresponding to the type of error if there was an error, or False otherwise.
        """

        if("error" in response):
            for error in Error:
                if(response["error"] == error.value):
                    return error
            else:
                return Error.UNKOWN
        else:
            return False

    @staticmethod
    def enforce_ratelimit():
        """
        Enforces the ratelimit by sleeping the thread until it's safe to make requests again.
        """

        difference = datetime.now() - Loader.start_time
        seconds_passed = difference.seconds
        if(seconds_passed > Loader.RATELIMIT_RESET):
            return

        # sleep the remainder of the reset cycle so we guarantee it's been that long since the first request
        sleep_seconds = Loader.RATELIMIT_RESET - seconds_passed
        print("Ratelimited. Sleeping for {} seconds".format(sleep_seconds))
        time.sleep(sleep_seconds)
