from datetime import datetime
import time
import base64
import logging
from lzma import LZMAError
from functools import lru_cache

import requests
from requests import RequestException
import circleparse
import ossapi

from circleguard.user_info import UserInfo
from circleguard.enums import Error, ModCombination
from circleguard.exceptions import (InvalidArgumentsException, APIException, CircleguardException,
                        RatelimitException, InvalidKeyException, ReplayUnavailableException, UnknownAPIException,
                        InvalidJSONException, NoInfoAvailableException)
from circleguard.utils import TRACE, span_to_list

def request(function):
    """
    A decorator that handles :mod:`requests` and api related exceptions, as
    well as resetting our ratelimits if appropriate.

    Parameters
    ----------
    function: callable
        The function to wrap.

    Notes
    -----
    Should be wrapped around any function that makes a request; to the api or
    otherwise.

    If it has been more than :data:`Loader.RATELIMIT_RESET` since
    :data:`Loader.start_time`, sets :data:`Loader.start_time` to be
    :func:`datetime.now <datetime.datetime.now>`.
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
    A decorator that checks if the passed
    :class:`~circleguard.user_info.UserInfo` has its replay cached. If so,
    returns a :class:`~circleguard.replay.Replay` instance from the cached data.
    Otherwise, calls and returns the `function` as normal.

    Notes
    -----
    ``self`` and ``user_info`` **MUST** be the first and second arguments to
    the function, respectively.

    Returns
    -------
    :class:`~circleguard.replay.Replay` or Unknown:
        A :class:`~circleguard.replay.Replay` instance from the cached data
        if it was cached, or the return value of the function if not.
    """

    def wrapper(*args, **kwargs):
        self = args[0]
        user_info = args[1]

        if self.cacher is None:
            return function(*args, **kwargs)

        lzma = self.cacher.check_cache(user_info.map_id, user_info.user_id, user_info.mods)
        if lzma:
            replay_data = circleparse.parse_replay(lzma, pure_lzma=True).play_data
            return replay_data
        else:
            return function(*args, **kwargs)
    return wrapper

class Loader():
    """
    Manages interactions with the osu api, using the :mod:`ossapi` wrapper.

    Parameters
    ----------
    key: str
        A valid api key. Can be retrieved from https://osu.ppy.sh/p/api/.
    cacher: :class:`~circleguard.cacher.Cacher`
        A :class:`~circleguard.cacher.Cacher` instance to manage
        replay loading/caching. If `None`, replays will not be loaded from
        the cache or cached to the database.

    Notes
    -----
    If the api ratelimits the key, we wait until our ratelimits are refreshed
    and retry the request. Because the api does not provide the time until the
    next refresh (and we do not periodically retry the key), if the key is
    ratelimited because of an interaction not managed by this class,
    the class may wait more time than necessary for the key to refresh.
    """

    RATELIMIT_RESET = 60 # time in seconds until the api refreshes our ratelimits
    start_time = datetime.min # when we started our requests cycle


    def __init__(self, key, cacher=None):
        self.log = logging.getLogger(__name__)
        self.api = ossapi.ossapi(key)
        self.cacher = cacher

    @request
    def user_info(self, map_id, num=None, user_id=None, mods=None, limit=True, span=None):
        """
        Retrieves user infos from ``map_id``.

        Parameters
        ----------
        map_id: int
            The map id to retrieve user info for.
        num: int
            The number of user infos on the map to retrieve.
        user_id: int
            If passed, only retrieve user info on ``map_id`` for this user.
            Note that this is not necessarily limited to just the user's top
            score on the map. See ``limit``.
        mods: :class:`~.ModCombination`
            The mods to limit user infos to. ie only return user infos with
            mods that match ``mods``.
        limit: bool
            Whether to limit to only one response. Only has an effect if
            ``user_id`` is passed. If ``limit`` is ``True``, will only return
            the top scoring user info by ``user_id``. If ``False``, will return
            all scores by ``user_id``.
        span: str
            A comma separated list of ranges of top replays on the map to
            retrieve. ``span="1-3,6,2-4"`` -> replays in the range
            ``[1,2,3,4,6]``.

        Returns
        -------
        list[:class:`~.UserInfo`]
            The user infos as specified by the arguments.
        :class:`~.UserInfo`
            If ``limit`` is ``True`` and ``user_id`` is passed.

        Notes
        -----
        One of ``num``, ``user_id``, and ``span`` must be passed, but not both
        ``num`` and either ``user_id`` or ``span``.

        Raises
        ------
        NoInfoAvailableException
            If there is no info available for the given parameters.
        """

        # we have to define a new variable to hold locals - otherwise when we call it twice inside the dict comprehension,
        # it rebinds to the comp scope and takes on different locals which is real bad. I spent many-a-hour figuring this out,
        # and if anyone has a more elegant solution I'm all ears.
        locals_ = locals()
        self.log.log(TRACE, "Loading user info on map %d with options %s",
                            map_id, {k: locals_[k] for k in locals_ if k != 'self'})

        if num and (num > 100 or num < 1):
            raise InvalidArgumentsException("The number of top plays to fetch must be between 1 and 100 inclusive!")

        if not bool(user_id) ^ (bool(num) or bool(span)):
            raise InvalidArgumentsException("One of num, user_id, or span must be passed, but not both num and either user_id or span")
        if span:
            span_list = span_to_list(span)
            num = max(span_list)
        response = self.api.get_scores({"m": "0", "b": map_id, "limit": num, "u": user_id, "mods": mods if mods is None else mods.value})
        Loader.check_response(response)
        if span:
            # filter out anything not in our span
            response = [response[i-1] for i in span_list]
        # yes, it's necessary to cast the str response to int before bool - all strings are truthy.
        # strptime format from https://github.com/ppy/osu-api/wiki#apiget_scores
        infos = [UserInfo(datetime.strptime(x["date"], "%Y-%m-%d %H:%M:%S"), map_id, int(x["user_id"]), str(x["username"]), int(x["score_id"]),
                          ModCombination(int(x["enabled_mods"])), bool(int(x["replay_available"]))) for x in response]

        return infos[0] if (limit and user_id) else infos # limit only applies if user_id was set


    @request
    def get_user_best(self, user_id, num=None, span=None, mods=None):
        """
        Gets the top 100 best plays for the given user.

        Parameters
        ----------
        user_id: str
            The user id to get best plays of.
        num: int
            The number of top plays to retrieve. Must be between 1 and 100.
        span: str
            A comma separated list of ranges of top plays to retrieve.
            ``span="1-3,6,2-4"`` -> replays in the range ``[1,2,3,4,6]``.

        Returns:
            A list of Integer map_ids for the given number of the user's top plays.

        Raises
        ------
        InvalidArgumentsException
            If ``num`` or ``span`` is not between ``1`` and ``100`` inclusive.
        """

        self.log.log(TRACE, "Retrieving the best %d plays of user %d", num, user_id)
        if span:
            span_list = span_to_list(span)
            num = max(span_list)
        if num < 1 or num > 100:
            raise InvalidArgumentsException("The number of best user plays to fetch must be between 1 and 100 inclusive!")

        response = self.api.get_user_best({"m": "0", "u": user_id, "limit": num})
        Loader.check_response(response)
        if mods:
            _response = []
            for r in response:
                if ModCombination(int(r["enabled_mods"])) == mods:
                    _response.append(r)
            response = _response

        if span:
            response = [response[i-1] for i in span_list]
        return [UserInfo(datetime.strptime(r["date"], "%Y-%m-%d %H:%M:%S"), int(r["beatmap_id"]), int(r["user_id"]),
                self.username(int(r["user_id"])), int(r["score_id"]), ModCombination(int(r["enabled_mods"])),
                bool(int(r["replay_available"]))) for r in response]


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
        response = self.api.get_replay({"m": "0", "b": map_id, "u": user_id, "mods": mods if mods is None else mods.value})
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
        if cache and self.cacher is not None:
            self.cacher.cache(lzma_bytes, user_info)
        return replay_data

    @lru_cache()
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

    @lru_cache()
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

    @lru_cache()
    def username(self, user_id):
        """
        The inverse of :meth:`~circleguard.loader.Loader.user_id`. Retrieves
        the username of the given user id.
        """
        response = self.api.get_user({"u": user_id, "type": "id"})
        if response == []:
            return ""
        else:
            return response[0]["username"]

    @staticmethod
    def check_response(response):
        """
        Checks the given api response for any kind of error or
        unexpected response.

        Args:
            String response: The api-returned response to check.

        Raises:
            An Error corresponding to the type of error if there is an error,
            or NoInfoAvailable if the response is empty. The mappings
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
            raise NoInfoAvailableException("No info was available from the api for the given arguments.")



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
