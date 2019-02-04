import requests
from datetime import datetime
import time
import base64
import sys

from requests import RequestException

from enums import Error
from config import API_SCORES_ALL, API_SCORES_USER, API_REPLAY
from exceptions import InvalidArgumentsException, APIException, CircleguardException, RatelimitException, InvalidKeyException, ReplayUnavailableException

def request(function):
    """
    Decorator intended to appropriately handle all request and api related exceptions.
    """

    def wrapper(*args, **kwargs):
        # catch them exceptions boy
        ret = None
        try:
            ret = function(*args, **kwargs)
        except RatelimitException:
            Loader.enforce_ratelimit()
            # wrap function with the decorator then call decorator
            ret = request(function)(*args, **kwargs)
        except InvalidKeyException as e:
            print(str(e))
            sys.exit(0)
        except RequestException as e:
            print("Request exception: {}. Sleeping for 5 seconds then retrying".format(e))
            time.sleep(10)
            ret = request(function)(*args, **kwargs)
        except ReplayUnavailableException as e:
            print(str(e))
            ret = None
        return ret
    return wrapper

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

        raise CircleguardException("This class is not meant to be instantiated. Use the static methods instead.")

    @staticmethod
    @request
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
            raise InvalidArgumentsException("The number of top plays to fetch must be between 2 and 100 inclusive!")
        response = requests.get(API_SCORES_ALL.format(map_id, num)).json()
        error = Loader.check_response(response)
        if(error):
            for error2 in Error:
                if(error == error2):
                    raise error.value[1](error.value[2])

        info = {x["user_id"]: [x["username"], x["score_id"], int(x["enabled_mods"])] for x in response} # map user id to username, score id and mod bit
        return info

    @staticmethod
    @request
    @api
    def user_info(map_id, user_id):
        """
        Returns a dict mapping a user_id to a list containing their [username, replay_id, enabled mods] on a given map.

        Args:
            String map_id: The map id to get the replay_id from.
            String user_id: The user id to get the replay_id from.
        """

        response = requests.get(API_SCORES_USER.format(map_id, user_id)).json()
        error = Loader.check_response(response)
        if(error):
            for error2 in Error:
                if(error == error2):
                    raise error.value[1](error.value[2])

        info = {x["user_id"]: [x["username"], x["score_id"], int(x["enabled_mods"])] for x in response} # map user id to username, score id and mod bit,
                                                                                                        # should only be one response
        return info

    @staticmethod
    @request
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
            APIException if the api responds with an error we don't know.
        """

        print("Requesting replay by {} on map {}".format(user_id, map_id))
        response = requests.get(API_REPLAY.format(map_id, user_id)).json()

        error = Loader.check_response(response)
        if(error):
            for error2 in Error:
                if(error == error2):
                    raise error.value[1](error.value[2])

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
                if(response["error"] == error.value[0]):
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
