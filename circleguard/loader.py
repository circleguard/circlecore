from datetime import datetime
import time
import base64
import sys

from requests import RequestException
import osrparse
import osuAPI

from online_replay import OnlineReplay
from enums import Error
from exceptions import InvalidArgumentsException, APIException

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


def check_cache(function):
    """
    Decorator that checks if the replay by the given user_id on the given map_id is already cached.
    If so, returns a Replay instance from the cached string instead of requesting it from the api.

    Note that cacher, map_id, user_id, replay_id, and enabled_mods must be the first, second, third, fifth, and sixth arguments to the function respectively.
    (ignoring the self argument)

    Returns:
        A Replay instance from the cached replay if it was cached, or the return value of the function if not.
    """

    def wrapper(*args, **kwargs):
        self = args[0]
        cacher = args[1]
        map_id = args[2]
        user_id = args[3]
        replay_id = args[5]
        enabled_mods = args[6]
        lzma = cacher.check_cache(map_id, user_id)
        if(lzma):
            replay_data = osrparse.parse_replay(lzma, pure_lzma=True).play_data
            self.loaded += 1
            return OnlineReplay(replay_data, user_id, enabled_mods, replay_id=replay_id)
        else:
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


    def __init__(self, total, key):
        """
        Initializes a Loader instance.
        """

        self.total = total
        self.loaded = 0
        self.api = osuAPI.OsuAPI(key)

    @api
    def users_info(self, map_id, num):
        """
        Returns a dict mapping each user_id to a list containing [username, replay_id, enabled mods]
        for the top given number of replays on the given map.

        EX: {"1234567": ["tybug", "295871732", 15]} # numbers may not be accurate to true mod bits or user ids

        Args:
            String map_id: The map id to get a list of users from.
            Integer num: The number of ids to fetch.
        """

        if(num > 100 or num < 2):
            raise InvalidArgumentsException("The number of top plays to fetch must be between 2 and 100 inclusive!")
        response = self.api.get_scores({"m": "0", "b": map_id, "limit": num})
        if(Loader.check_response(response)):
            self.enforce_ratelimit()
            return self.users_info(map_id, num)

        info = {x["user_id"]: [x["username"], x["score_id"], int(x["enabled_mods"])] for x in response} # map user id to username, score id and mod bit
        return info

    @api
    def user_info(self, map_id, user_id):
        """
        Returns a dict mapping a user_id to a list containing their [username, replay_id, enabled mods] on a given map.

        Args:
            String map_id: The map id to get the replay_id from.
            String user_id: The user id to get the replay_id from.
        """

        response = self.api.get_scores({"m": "0", "b": map_id, "u": user_id})
        if(Loader.check_response(response)):
            self.enforce_ratelimit()
            return self.user_info(map_id, user_id)
        info = {x["user_id"]: [x["username"], x["score_id"], int(x["enabled_mods"])] for x in response} # map user id to username, score id and mod bit,
                                                                                                        # should only be one response
        return info

    @api
    def replay_data(self, map_id, user_id):
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
        response = self.api.get_replay({"m": "0", "b": map_id, "u": user_id})

        error = Loader.check_response(response)
        if(error == Error.NO_REPLAY):
            print("Could not find any replay data for user {} on map {}, skipping".format(user_id, map_id))
            return None
        elif(error == Error.RETRIEVAL_FAILED):
            print("Replay retrieval failed for user {} on map {}, skipping".format(user_id, map_id))
            return None
        elif(error == Error.RATELIMITED):
            self.enforce_ratelimit()
            return self.replay_data(map_id, user_id)
        elif(error == Error.UNKOWN):
            raise APIException("unkown error when requesting replay by {} on map {}. Please lodge an issue with the devs immediately".format(user_id, map_id))

        self.loaded += 1

        return base64.b64decode(response["content"])


    @api
    def replay_from_user_info(self, cacher, map_id, user_info):
        """
        Creates a list of Replay instances for the users listed in user_info on the given map.

        Args:
            Cacher cacher: A cacher object containing a database connection.
            String map_id: The map_id to download the replays from.
            Dictionary user_info: A dict mapping user_ids to a list containing [username, replay_id, enabled mods] on the given map.
                                  See Loader.users_info

        Returns:
            A list of Replay instances from the given information, with entries with no replay data available excluded.
        """

        replays = [self.replay_from_map(cacher, map_id, user_id, replay_info[0], replay_info[1], replay_info[2]) for user_id, replay_info in user_info.items()]
        return replays

    @api
    @check_cache
    def replay_from_map(self, cacher, map_id, user_id, username, replay_id, enabled_mods):
        """
        Creates an OnlineReplay instance from a replay by the given user on the given map.

        Args:
            Cacher cacher: A cacher object containing a database connection.
            String map_id: The map_id to download the replay from.
            String user_id: The user id to download the replay of.
                            Also used as the username of the Replay.
            String replay_id: The id of the replay we are retrieving (used to cache).
            Integer enabled_mods: The base10 number representing the enabled mods

        Returns:
            The Replay instance created with the given information, or None if the replay was not available.
        """

        lzma_bytes = self.replay_data(map_id, user_id)
        if(lzma_bytes is None):
            return None
        parsed_replay = osrparse.parse_replay(lzma_bytes, pure_lzma=True)
        replay_data = parsed_replay.play_data
        cacher.cache(map_id, user_id, lzma_bytes, replay_id)
        return OnlineReplay(replay_data, username, enabled_mods, replay_id)

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

    def enforce_ratelimit(self):
        """
        Enforces the ratelimit by sleeping the thread until it's safe to make requests again.
        """

        difference = datetime.now() - Loader.start_time
        seconds_passed = difference.seconds
        if(seconds_passed > Loader.RATELIMIT_RESET):
            return

        # sleep the remainder of the reset cycle so we guarantee it's been that long since the first request
        sleep_seconds = Loader.RATELIMIT_RESET - seconds_passed
        print(f"Ratelimited, sleeping for {sleep_seconds} seconds. "
              f"{self.loaded} out of {self.total} maps loaded. ETA ~ {int((self.total-self.loaded)/10)+1} min")
        time.sleep(sleep_seconds)
