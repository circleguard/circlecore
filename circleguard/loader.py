from datetime import datetime
import time
import base64
import sys
import logging
from math import ceil

from requests import RequestException
import circleparse
import ossapi

from circleguard.replay import ReplayMap
from circleguard.user_info import UserInfo
from circleguard.enums import Error
from circleguard.exceptions import (InvalidArgumentsException, APIException, CircleguardException,
                        RatelimitException, InvalidKeyException, ReplayUnavailableException, UnknownAPIException)
from circleguard.utils import TRACE

def request(function):
    """
    Decorator intended to appropriately handle all request and api related exceptions.

    Also checks if we can refresh the time at which we started our requests because
    it's been more than RATELIMIT_RESET since the first request of the cycle.

    If we've refreshed our ratelimits, sets start_time to be the current datetime.
    """

    def wrapper(*args, **kwargs):
        difference = datetime.now() - Loader.start_time
        if(difference.seconds > Loader.RATELIMIT_RESET):
            Loader.start_time = datetime.now()
        # catch them exceptions boy
        ret = None
        self = args[0]
        try:
            ret = function(*args, **kwargs)
        except RatelimitException:
            self._enforce_ratelimit()
            # wrap function with the decorator then call decorator
            ret = request(function)(*args, **kwargs)
        except InvalidKeyException as e:
            raise CircleguardException("The given key is invalid")
        except RequestException as e:
            self.log.warning("Request exception: {}. Likely a network issue; sleeping for 5 seconds then retrying".format(e))
            time.sleep(5)
            ret = request(function)(*args, **kwargs)
        except ReplayUnavailableException as e:
            self.log.warning("We expected a replay from the api, but it was unable to deliver it: {}".format(e))
            ret = None
        return ret
    return wrapper


def check_cache(function):
    """
    Decorator that checks if the replay by the given user_id on the given map_id is already
    cached. If so, returns a Replay instance from the cached data instead of requesting it
    from the api. Otherwise, it calls the function as normal.

    Note that self and user_info must be the first and second arguments to
    the function respectively.

    Returns:
        A Replay instance from the cached replay if it was cached,
        or the return value of the function if not.
    """

    def wrapper(*args, **kwargs):
        self = args[0]
        user_info = args[1]

        lzma = self.cacher.check_cache(user_info.map_id, user_info.user_id, user_info.mods)
        if(lzma):
            replay_data = circleparse.parse_replay(lzma, pure_lzma=True).play_data
            self.loaded += 1
            return replay_data
        else:
            return function(*args, **kwargs)
    return wrapper

class Loader():
    """
    Manages interactions with the osu api, using the ossapi wrapper.

    if the api ratelimits the key, we wait until we refresh our ratelimits and retry
    the request. Because the api does not provide the time until the next refresh (and we
    do not periodically retry the key), if the key is ratelimited outside of this class,
    the class may wait more time than necessary for the key to refresh.
    """

    RATELIMIT_RESET = 60 # time in seconds until the api refreshes our ratelimits
    start_time = datetime.min # when we started our requests cycle


    def __init__(self, cacher, key):
        """
        Initializes a Loader instance.
        """

        self.log = logging.getLogger(__name__)
        self.total = None
        self.loaded = 0
        self.api = ossapi.ossapi(key)
        self.cacher = cacher


    def new_session(self, total):
        """
        Resets the loaded replays to 0, and sets the total to the passed total.

        Intended to be called every time the loader is used for a different set of replay loadings -
        since a Loader instance is passed around to Comparer and Investigator, each with different
        amounts of replays to load, making new sessions is necessary to keep progress logs correct.
        """

        self.log.debug("Starting a new session with total %d", total)
        self.loaded = 0
        self.total = total


    @request
    def user_info(self, map_id, num=None, user_id=None, mods=None, limit=True):
        """
        Returns a list of UserInfo objects containing a user's
        (user_id, username, replay_id, enabled mods, replay available)
        on a given map.

        If limit and user_id is set, it will return a single UserInfo object, not a list.

        Args:
            Integer map_id: The map id to get the replay_id from.
            Integer user_id: The user id to get the replay_id from.
            Boolean limit: If set, will only return a user's top score (top response). Otherwise, will
                          return every response (every score they set on that map under different mods)
            Integer mods: The mods the replay info to retieve were played with.
        """

        # we have to define a new variable to hold locals - otherwise when we call it twice inside the dict comprehension,
        # it rebinds to the comp scope and takes on different locals which is real bad. I spent many-a-hour figuring this out,
        # and if anyone has a more elegant solution I'm all ears.
        locals_ = locals()
        self.log.log(TRACE, "Loading user info on map %d with options %s",
                            map_id, {k: locals_[k] for k in locals_ if k != 'self'})

        if(num and (num > 100 or num < 2)):
            raise InvalidArgumentsException("The number of top plays to fetch must be between 2 and 100 inclusive!")

        if(not bool(user_id) ^ bool(num)):
            raise InvalidArgumentsException("One of either num or user_id must be passed, but not both")

        response = self.api.get_scores({"m": "0", "b": map_id, "limit": num, "u": user_id, "mods": mods})
        Loader.check_response(response)
                                                                    # yes, it's necessary to cast the str response to int before bool - all strings are truthy.
        infos = [UserInfo(map_id, int(x["user_id"]), str(x["username"]), int(x["score_id"]), int(x["enabled_mods"]), bool(int(x["replay_available"]))) for x in response]

        return infos[0] if (limit and user_id) else infos # limit only applies if user_id was set


    @request
    def get_user_best(self, user_id, number):
        """
        Gets the top 100 best plays for the given user.

        Args:
            String user_id: The user id to get best plays of.
            Integer number: The number of top plays to retrieve. Must be between 1 and 100.

        Returns:
            A list of Integer map_ids for the given number of the user's top plays.

        Raises:
            InvalidArgumentsException if number is not between 1 and 100 inclusive.
        """

        self.log.log(TRACE, "Retrieving the best %d plays of user %d", number, user_id)
        if(number < 1 or number > 100):
            raise InvalidArgumentsException("The number of best user plays to fetch must be between 1 and 100 inclusive!")
        response = self.api.get_user_best({"m": "0", "u": user_id, "limit": number})

        Loader.check_response(response)

        return [int(x["beatmap_id"]) for x in response]


    @request
    def load_replay_data(self, map_id, user_id, mods=None):
        """
        Queries the api for replay data from the given user on the given map, with the given mods.

        Args:
            UserInfo user_info: The UserInfo representing this replay.
        Returns:
            The lzma bytes (b64 decoded response) returned by the api, or None if the replay was not available.

        Raises:
            CircleguardException if the loader instance has had a new session made yet.
            APIException if the api responds with an error we don't know.
        """

        self.log.log(TRACE, "Requesting replay data by user %d on map %d with mods %s", user_id, map_id, mods)
        if(self.total is None):
            raise CircleguardException("loader#new_session(total) must be called after instantiation, before any replay data is loaded.")

        response = self.api.get_replay({"m": "0", "b": map_id, "u": user_id, "mods": mods})

        Loader.check_response(response)
        self.loaded += 1

        return base64.b64decode(response["content"])

    @check_cache
    def replay_data(self, user_info, cache=None):
        """
        Loads the replay data specified by the user info.

        Args:
            UserInfo user_info: The UserInfo object representing this replay.

        Returns:
            The play_data field of an circleparse.Replay instance created from the replay data received from the api,
            or None if the replay was not available.

        Raises:
            UnknownAPIException if replay_available was 1, but we did not receive replay data from the api.
        """

        user_id = user_info.user_id
        map_id = user_info.map_id
        mods = user_info.mods
        if(not user_info.replay_available):
            self.log.debug("Replay data by user %d on map %d with mods %s not available", user_id, map_id, mods)
            return None

        lzma_bytes = self.load_replay_data(map_id, user_id, mods)
        if(lzma_bytes is None):
            raise UnknownAPIException("The api guaranteed there would be a replay available, but we did not receive any data. "
                                     "Please report this to the devs, who will open an issue on osu!api if necessary.")
        parsed_replay = circleparse.parse_replay(lzma_bytes, pure_lzma=True)
        replay_data = parsed_replay.play_data
        self.cacher.cache(lzma_bytes, user_info, should_cache=cache)
        return replay_data

    @staticmethod
    def check_response(response):
        """
        Checks the given api response for any kind of error or unexpected response.

        Args:
            String response: The api-returned response to check.

        Raises:
            An Error corresponding to the type of error if there was an error. The mappings
            for the api error message and its corresponding error are in circleguard.enums.
        """

        if("error" in response):
            for error in Error:
                if(response["error"] == error.value[0]):
                    raise error.value[1](error.value[2])
            else:
                raise Error.UNKNOWN.value[1](Error.UNKNOWN.value[2]) # pylint: disable=unsubscriptable-object
                # pylint is dumb because Error is an enum and this is totally legal

    def _enforce_ratelimit(self):
        """
        Enforces the api ratelimit by sleeping the thread until it's safe to make requests again.
        """

        difference = datetime.now() - Loader.start_time
        seconds_passed = difference.seconds
        if(seconds_passed > Loader.RATELIMIT_RESET):
            self.log.debug("More than a minute has passed since our last ratelimit, not sleeping")
            return

        # sleep the remainder of the reset cycle so we guarantee it's been that long since the first request
        sleep_seconds = Loader.RATELIMIT_RESET - seconds_passed

        self.log.info("Ratelimited, sleeping for %s seconds. %d of %d replays loaded. "
            "ETA ~ %d min", sleep_seconds, self.loaded, self.total, ceil((self.total-self.loaded)/10))
        time.sleep(sleep_seconds)
