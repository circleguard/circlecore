from datetime import datetime
import time
import base64
import logging
from lzma import LZMAError

import requests
from requests import RequestException
import circleparse
import ossapi

from circleguard.user_info import UserInfo
from circleguard.enums import Error
from circleguard.exceptions import (InvalidArgumentsException, APIException, CircleguardException,
                        RatelimitException, InvalidKeyException, ReplayUnavailableException, UnknownAPIException,
                        InvalidJSONException, NoInfoAvailable)
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
        except InvalidJSONException as e:
            self.log.warning("Invalid json exception: {}. API likely having issues; sleeping for 3 seconds then retrying".format(e))
            time.sleep(3)
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

        if self.cacher is None:
            return function(*args, **kwargs)

        lzma = self.cacher.check_cache(user_info.map_id, user_info.user_id, user_info.mods)
        if lzma :
            replay_data = circleparse.parse_replay(lzma, pure_lzma=True).play_data
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


    def __init__(self, key, cacher=None):
        """
        Initializes a Loader instance. If a Cacher is not provided,
        scores will not be loaded from cache or cached to the databse.
        """

        self.log = logging.getLogger(__name__)
        self.api = ossapi.ossapi(key)
        self.cacher = cacher

    @request
    def get_beatmap(self, map_id):
        """
        Returns the content of the beatmap of the given map. This request is
        not ratelimited and does not require an api key. Because of this, treat
        this endpoint with caution - the osu-tools repository uses this endpoint
        and peppy has said it is "ok to use for now", but even so it is not in
        the same category as other api endpoints.
        """
        return requests.get(f"https://osu.ppy.sh/osu/{map_id}").content

    @request
    def user_info(self, map_id, num=None, user_id=None, mods=None, limit=True):
        """
        Returns a list of UserInfo objects containing a user's
        (timestamp, map_id, user_id, username, replay_id, mods, replay_available)
        on the given map.

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

        if(num and (num > 100 or num < 1)):
            raise InvalidArgumentsException("The number of top plays to fetch must be between 1 and 100 inclusive!")

        if(not bool(user_id) ^ bool(num)):
            raise InvalidArgumentsException("One of either num or user_id must be passed, but not both")

        response = self.api.get_scores({"m": "0", "b": map_id, "limit": num, "u": user_id, "mods": mods})
        Loader.check_response(response)
        # yes, it's necessary to cast the str response to int before bool - all strings are truthy.
        # strptime format from https://github.com/ppy/osu-api/wiki#apiget_scores
        infos = [UserInfo(datetime.strptime(x["date"], "%Y-%m-%d %H:%M:%S"), map_id, int(x["user_id"]), str(x["username"]), int(x["score_id"]),
                          int(x["enabled_mods"]), bool(int(x["replay_available"]))) for x in response]

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
        response = self.api.get_replay({"m": "0", "b": map_id, "u": user_id, "mods": mods})
        Loader.check_response(response)

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
        try:
            parsed_replay = circleparse.parse_replay(lzma_bytes, pure_lzma=True)
        # see https://github.com/circleguard/circlecore/issues/61
        # api sometimes returns corrupt replays
        except LZMAError:
            self.log.warning("lzma from %r could not be decompressed, api returned corrupt replay", user_info)
            return None
        replay_data = parsed_replay.play_data
        if self.cacher is not None:
            self.cacher.cache(lzma_bytes, user_info, should_cache=cache)
        return replay_data

    def map_id(self, map_hash):
        """
        Retrieves the corresponding map id for the given map_hash from the api.

        Returns:
            The corresponding map id, or 0 if the api returned no matches.
        """

        response = self.api.get_beatmaps({"h": map_hash})
        if response == []:
            return 0
        else:
            return int(response[0]["beatmap_id"])

    def user_id(self, username):
        """
        Retrieves the corresponding user id for the given username from the api.
        Note that the api currently has no method to keep track of name changes,
        meaning this method will return 0 for previous usernames of a user, rather
        than their true id.

        Returns:
            The corresponding user id, or 0 if the api returned no matches.
        """

        response = self.api.get_user({"u": username, "type": "string"})
        if response == []:
            return 0
        else:
            return int(response[0]["user_id"])

    @staticmethod
    def check_response(response):
        """
        Checks the given api response for any kind of error or unexpected response.

        Args:
            String response: The api-returned response to check.

        Raises:
            An Error corresponding to the type of error if there is an error, or
            NoInfoAvailable if the response is empty. The mappings
            for the api error message and its corresponding error are in circleguard.enums.
        """

        if("error" in response):
            for error in Error:
                if(response["error"] == error.value[0]):
                    raise error.value[1](error.value[2])
            else:
                raise Error.UNKNOWN.value[1](Error.UNKNOWN.value[2]) # pylint: disable=unsubscriptable-object
                # pylint is dumb because Error is an enum and this is totally legal
        if not response: # response is empty
            raise NoInfoAvailable("No info was available from the api for the given arguments.")



    def _enforce_ratelimit(self):
        """
        Enforces the api ratelimit by sleeping the thread until it's safe to make requests again.
        """

        difference = datetime.now() - Loader.start_time
        seconds_passed = difference.seconds

        # sleep the remainder of the reset cycle so we guarantee it's been that long since the first request
        sleep_seconds = Loader.RATELIMIT_RESET - seconds_passed
        self._ratelimit(sleep_seconds)

    def _ratelimit(self, length):
        """
        Sleeps the thread for the specified amount of time. Called by #_enforce_ratelimit.

        Split into two functions mostly to allow Loader subclasses to overload a single function and easily
        get the time the Loader will be ratelimited for.
        """
        self.log.info("Ratelimited, sleeping for %s seconds.", length)
        time.sleep(length)
