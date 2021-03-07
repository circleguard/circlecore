from datetime import datetime
import time
import base64
import logging
from lzma import LZMAError
from functools import lru_cache
from enum import Enum

from requests import RequestException
import osrparse
import ossapi

from circleguard.mod import Mod
from circleguard.utils import TRACE
from circleguard.span import Span


class APIException(Exception):
    """An error involving the osu! api."""

class NoInfoAvailableException(APIException):
    """The api returned no information for the given arguments."""

class UnknownAPIException(APIException):
    """An api error that we were not prepared to handle."""

class InternalAPIException(APIException):
    """
    An api error that we know how to handle, and will do so automatically.
    """

class InvalidKeyException(InternalAPIException):
    """An api key was rejected by the api."""

class RatelimitException(InternalAPIException):
    """The api has ratelimit an api key."""

class InvalidJSONException(InternalAPIException):
    """The api returned an invalid json response."""

class ReplayUnavailableException(InternalAPIException):
    """
    We expected a replay from the api but the api was unable to deliver it.
    """

# Strings taken from osu api error responses. Format is
# [api response, exception class type, details to pass to an exception]
class Error(Enum):
    NO_REPLAY         = ["Replay not available.", ReplayUnavailableException,
        "Could not find any replay data. Skipping"]
    RATELIMITED       = ["Requesting too fast! Slow your operation, cap'n!",
        RatelimitException, "We were ratelimited. Waiting it out"]
    RETRIEVAL_FAILED  = ["Replay retrieval failed.", ReplayUnavailableException,
        "Replay retrieval failed. Skipping"]
    INVALID_KEY       = ["Please provide a valid API key.", InvalidKeyException,
        "Please provide a valid api key"]
    INVALID_JSON      = ["The api broke.", InvalidJSONException,
        "The api returned an invalid json response, retrying"]
    UNKNOWN           = ["Unknown error.", UnknownAPIException,
        "Unknown error when requesting a replay."]


class ReplayInfo():
    """
    A container class representing all the information we get about a replay
    from the api.

    Parameters
    ----------
    timestamp: :class:`datetime.datetime`
        When this replay was set.
    map_id: int
        The id of the map the replay was played on.
    user_id: int
        The id of the player who played the replay.
    username: str
        The username of the player who played the replay.
    replay_id: int
        The id of the replay.
    mods: :class:`~circleguard.mod.ModCombination`
        The mods the replay was played with.
    replay_available: bool
        Whether this replay is available from the api or not.
    """
    def __init__(self, timestamp, map_id, user_id, username, replay_id, mods, \
        replay_available):
        self.timestamp = timestamp
        self.map_id = map_id
        self.user_id = user_id
        self.username = username
        self.replay_id = replay_id
        self.mods = mods
        self.replay_available = replay_available


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
        if difference.seconds > Loader.RATELIMIT_RESET:
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
            self.log.warning(f"Invalid json exception: {e}. API likely having "
                "issues; sleeping for 3 seconds then retrying")
            time.sleep(3)
            ret = request(function)(*args, **kwargs)
        except RequestException as e:
            self.log.warning(f"Request exception: {e}. Likely a network issue; "
                "sleeping for 5 seconds then retrying")
            time.sleep(5)
            ret = request(function)(*args, **kwargs)
        except ReplayUnavailableException as e:
            self.log.warning("We expected a replay from the api, but it was "
                f"unable to deliver it: {e}")
            ret = None
        return ret
    return wrapper


def check_cache(function):
    """
    A decorator that checks if the passed
    :class:`~.ReplayInfo` has its replay cached. If so,
    returns a :class:`~circleguard.loadables.Replay` instance from the cached
    data. Otherwise, calls and returns the `function` as normal.

    Parameters
    ----------
    function: callable
        The function to wrap.

    Notes
    -----
    ``self`` and ``replay_info`` **MUST** be the first and second arguments to
    the function, respectively.

    Returns
    -------
    :class:`~circleguard.loadables.Replay` or Unknown:
        A :class:`~circleguard.loadables.Replay` instance from the cached data
        if it was cached, or the return value of the function if not.
    """

    def wrapper(*args, **kwargs):
        self = args[0]
        replay_info = args[1]

        if self.cacher is None:
            return function(*args, **kwargs)

        decompressed_lzma = self.cacher.check_cache(replay_info)
        if decompressed_lzma:
            parsed = osrparse.parse_replay(decompressed_lzma, \
                pure_lzma=True, decompressed_lzma=True)
            return parsed.play_data
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
    next refresh (and we do not use exponential backoff or another retry
    strategy), if the key is ratelimited because of an interaction not managed
    by this class, the class may wait more time than necessary for the key to
    refresh.
    """

    # the maximum number of replay info available through the respective api
    # calls. Note that osu! stores at least the top 1000 replays, but does not
    # make these discoverable unless you know the exact user id, map id, and
    # mods of the replay.
    MAX_MAP_SPAN = Span("1-100")
    MAX_USER_SPAN = Span("1-100")
    # time in seconds until the api refreshes our ratelimits
    RATELIMIT_RESET = 60
    # when we started our requests cycle
    start_time = datetime.min


    def __init__(self, key, cacher=None):
        self.log = logging.getLogger(__name__)
        self.api = ossapi.ossapi(key)
        self.cacher = cacher

    @request
    def replay_info(self, map_id, span=None, user_id=None, mods=None, \
        limit=True):
        """
        Retrieves replay infos from a map's leaderboard.

        Parameters
        ----------
        map_id: int
            The map id to retrieve replay info for.
        span: Span
            A comma separated list of ranges of top replays on the map to
            retrieve. ``span="1-3,6,2-4"`` -> replays in the range
            ``[1,2,3,4,6]``.
        user_id: int
            If passed, only retrieve replay info on ``map_id`` for this user.
            Note that this is not necessarily limited to just the user's top
            score on the map. See ``limit``.
        mods: :class:`~.ModCombination`
            If passed, will only retrieve replay infos for scores that were
            played with the given mods.
        limit: bool
            Whether to limit to only one response. Only has an effect if
            ``user_id`` is passed. If ``limit`` is ``True``, will only return
            the top scoring replay info by ``user_id``. If ``False``, will
            return all scores by ``user_id``.

        Returns
        -------
        list[:class:`~.ReplayInfo`]
            The replay infos representing the map's leaderboard.
        :class:`~.ReplayInfo`
            If ``limit`` is ``True`` and ``user_id`` is passed.

        Notes
        -----
        One of ``user_id`` or ``span`` must be passed.

        Raises
        ------
        NoInfoAvailableException
            If there is no info available for the given parameters.
        """

        # we have to define a new variable to hold locals - otherwise when we
        # call it twice inside the dict comprehension, it rebinds to the comp
        # scope and takes on different locals.
        locals_ = locals()
        self.log.log(TRACE, "Loading replay info on map %d with options %s",
            map_id, {k: locals_[k] for k in locals_ if k != 'self'})

        if not (span or user_id):
            raise ValueError("One of user_id or span must be passed, but not "
                "both")
        api_limit = None
        if span:
            api_limit = max(span)
        mods = None if mods is None else mods.value
        request_data = {"m": "0", "b": map_id, "limit": api_limit, "u": user_id,
            "mods": mods}
        response = self.api.get_scores(request_data)
        try:
            Loader.check_response(response)
        except NoInfoAvailableException:
            # The logic below allows us to load eg
            # ``Map(221777, mods=Mod.SO + Mod.PF + Mod.HT)`` or some equally
            # absurd mod combination for which there are no replays, and have
            # that loading not throw ``NoInfoAvailableException``. Instead,
            # the map's replays list will just be empty.
            # However, we only want to apply this if we're loading a map, ie
            # ``span`` has been passed. If ``user_id`` was passed instead, raise
            # the exception as usual.
            if user_id:
                raise
            # the osu! api doesn't distinguish between a map not existing, and
            # no scores having been set on that map for a particular mod
            # combination - both are empty responses which will trigger a no
            # info available exception. We need to figure out which case has
            # occurred here to determine if we should raise or not.
            beatmap_response = self.api.get_beatmaps({"b": map_id})
            # If the beatmap does not exist, this response will be empty.
            if not beatmap_response:
                raise
            # else, ignore the exception.

        if span:
            # Remove indices that would error when indexing ``response``.
            # we index at [i-1], so use <= instead of <
            _span = {x for x in span if x <= len(response)}
            # filter out anything not in our span
            response = [response[i-1] for i in _span]
        # need to cast replay_available to int before bool since the api returns
        # either ``"0"`` or ``"1"`` and all strings are truthy
        # strptime format from https://github.com/ppy/osu-api/wiki#apiget_scores
        infos = [ReplayInfo(datetime.strptime(x["date"], "%Y-%m-%d %H:%M:%S"),
            map_id, int(x["user_id"]), str(x["username"]), int(x["score_id"]),
            Mod(int(x["enabled_mods"])), bool(int(x["replay_available"])))
            for x in response]

        # limit only applies if user_id was set
        return infos[0] if (limit and user_id) else infos


    @request
    def get_user_best(self, user_id, span, mods=None):
        """
        Retrieves replay infos from a user's top plays.

        Parameters
        ----------
        user_id: int
            The user id to get best plays of.
        span: Span
            A comma separated list of ranges of top plays to retrieve.
            ``span="1-3,6,2-4"`` -> replays in the range ``[1,2,3,4,6]``.
        mods: :class:`~.ModCombination`
            If passed, will only retrieve replay infos for scores that were
            played with the given mods.

        Returns
        -------
        list[:class:`~.ReplayInfo`]
            The replay infos representing the user's top plays.
        """
        locals_ = locals()
        self.log.log(TRACE, "Loading user best of %s with options %s",
            user_id, {k: locals_[k] for k in locals_ if k != 'self'})

        request_data = {"m": "0", "u": user_id, "limit": max(span)}
        response = self.api.get_user_best(request_data)
        Loader.check_response(response)
        if mods:
            _response = []
            for r in response:
                if Mod(int(r["enabled_mods"])) == mods:
                    _response.append(r)
            response = _response

        # remove span indices which would cause an index error because there
        # weren't that many replay infos returned by the api. eg if there
        # were 4 responses, remove any span above 4
        response_count = len(response)
        _span = [x for x in span if x <= response_count]

        response = [response[i-1] for i in _span]
        return [ReplayInfo(datetime.strptime(r["date"], "%Y-%m-%d %H:%M:%S"),
            int(r["beatmap_id"]), int(r["user_id"]),
            self.username(int(r["user_id"])), int(r["score_id"]),
            Mod(int(r["enabled_mods"])), bool(int(r["replay_available"])))
            for r in response]


    @request
    def load_replay_data(self, map_id, user_id, mods=None):
        """
        Retrieves replay data from the api.

        Parameters
        ----------
        map_id: int
            The map the replay was played on.
        user_id: int
            The user that played the replay.
        mods: :class:`~.ModCombination`
            The mods the replay was played with, or ``None`` for the highest
            scoring replay, regardless of mods.

        Returns
        -------
        str
            The lzma-encoded string, decoded from the base 64 api response,
            representing the replay.
        None
            If no replay data was available.

        Notes
        -----
        This is the low level implementation of :func:`~.replay_data`, handling
        the actual api request.
        """

        self.log.log(TRACE, "Requesting replay data by user %d on map %d with "
            "mods %s", user_id, map_id, mods)
        mods = None if mods is None else mods.value
        request_data = {"m": "0", "b": map_id, "u": user_id, "mods": mods}
        response = self.api.get_replay(request_data)
        Loader.check_response(response)
        return base64.b64decode(response["content"])

    @check_cache
    def replay_data(self, replay_info, cache=None):
        """
        Retrieves replay data from the api, or from the cache if it is already
        cached.

        Parameters
        ----------
        replay_info: :class:`~.ReplayInfo`
            The replay info representing the replay to retrieve.

        Returns
        -------
        list[:class:`osrparse.replay.ReplayEvent`]
            The replay events with attributes ``x``, ``y``,
            ``time_since_previous_action``, and ``keys_pressed``.
        None
            If no replay data was available.

        Raises
        ------
        UnknownAPIException
            If ``uxser_info.replay_available` was 1, but we did not receive
            replay data from the api.
        """

        user_id = replay_info.user_id
        map_id = replay_info.map_id
        mods = replay_info.mods
        if not replay_info.replay_available:
            self.log.debug("Replay data by user %d on map %d with mods %s not "
                "available", user_id, map_id, mods)
            return None

        lzma_bytes = self.load_replay_data(map_id, user_id, mods)
        if lzma_bytes is None:
            raise UnknownAPIException("The api guaranteed there would be a "
                "replay available, but we did not receive any data.")
        try:
            parsed_replay = osrparse.parse_replay(lzma_bytes, pure_lzma=True)
        # see https://github.com/circleguard/circlecore/issues/61
        # api sometimes returns corrupt replays
        except LZMAError:
            self.log.warning("lzma from %r could not be decompressed, api "
                "returned corrupt replay", replay_info)
            return None
        replay_data = parsed_replay.play_data
        if cache and self.cacher is not None:
            self.cacher.cache(lzma_bytes, replay_info)
        return replay_data

    # TODO make this check cache for the replay
    @request
    def replay_data_from_id(self, replay_id, cache):
        """
        Retrieves replay data from the api, given a replay id.

        Parameters
        ----------
        replay_id: int
            The id of the replay to retrieve data for.
        """
        response = self.api.get_replay({"s": replay_id})
        Loader.check_response(response)
        lzma = base64.b64decode(response["content"])
        replay_data = osrparse.parse_replay(lzma, pure_lzma=True).play_data
        # TODO cache the replay here, might require some restructring/double
        # checking everything will work because we only have its id, not map
        # or user id. In fact I think our db asserts map and user id are nonull
        # so insertion into old dbs probably won't work (and we'd have to change
        # the schema).
        # TODO include a db version in the db for future scenarios like this?
        # look into how that's typically done, maybe just a `VERSION` table with
        # a single row
        return replay_data

    @lru_cache()
    @request
    def map_id(self, map_hash):
        """
        Retrieves a map id from a corresponding map hash through the api.

        Parameters
        ----------
        map_hash: str
            The md5 hash of the map to get the id of.

        Returns
        -------
        int
            The map id that corresponds to ``map_hash``, or ``0`` if
            ``map_hash`` doesn't mach any map.

        Notes
        -----
        This function is wrapped in a :func:`functools.lru_cache` to prevent
        duplicate api calls.
        """

        response = self.api.get_beatmaps({"h": map_hash})
        try:
            Loader.check_response(response)
        except NoInfoAvailableException:
            return 0
        return int(response[0]["beatmap_id"])

    @lru_cache()
    @request
    def user_id(self, username):
        """
        Retrieves a user id from a corresponding username through the api.

        Parameters
        ----------
        username: str
            The username of the user to get the user id of.

        Returns
        -------
        int
            The user id that corresponds to ``username``, or ``0`` if
            ``username`` doesn't match any user.

        Notes
        -----
        The api redirects name changes to the current username. For instance,
        ``user_id("cookiezi")`` will return ``124493``, despite shige's current
        osu! username being ``chocomint``. However, I am not sure if this
        behavior is as well defined when someone else takes the previous name
        of a user.

        This function is case insensitive.

        This function is wrapped in a :func:`functools.lru_cache` to prevent
        duplicate api calls.
        """

        response = self.api.get_user({"u": username, "type": "string"})
        try:
            Loader.check_response(response)
        except NoInfoAvailableException:
            return 0
        return int(response[0]["user_id"])

    @lru_cache()
    @request
    def username(self, user_id):
        """
        Retrieves the username from a corresponding user id through the api.

        Parameters
        ----------
        user_id: int
            The user id of the user to get the username of.

        Returns
        -------
        str
            The username that corresponds to ``user_id``, or an empty string
            if ``user_id`` doesn't match any user.

        Notes
        -----
        This function is the inverse of
        :meth:`~circleguard.loader.Loader.user_id`.

        This function is wrapped in a :func:`functools.lru_cache` to prevent
        duplicate api calls.
        """
        response = self.api.get_user({"u": user_id, "type": "id"})
        try:
            Loader.check_response(response)
        except NoInfoAvailableException:
            return ""
        return response[0]["username"]

    @staticmethod
    def check_response(response):
        """
        Checks a response from the api for an error or empty response.

        Parameters
        ----------
        response: list or dict
            The response returned by the api.

        Raises
        ------
        One of :class:`~.Error`
            If an error exists in the response.
        NoInfoAvailable
            If the response is empty.
        """
        if "error" in response: # dict case
            for error in Error:
                if response["error"] == error.value[0]:
                    raise error.value[1](error.value[2])
            # don't know why pylint is throwing hands but this is definitely
            # legit
            raise Error.UNKNOWN.value[1](Error.UNKNOWN.value[2]) # pylint: disable=unsubscriptable-object
        if not response: # response is empty, list or dict case
            raise NoInfoAvailableException("No info was available from the api "
                "for the given arguments.")

    def _enforce_ratelimit(self):
        """
        Sleeps the thread until we have refreshed our ratelimits.
        """
        difference = datetime.now() - Loader.start_time
        seconds_passed = difference.seconds

        # sleep the remainder of the reset cycle so we guarantee it's been that
        # long since the first request
        sleep_seconds = Loader.RATELIMIT_RESET - seconds_passed
        self._ratelimit(sleep_seconds)

    def _ratelimit(self, length):
        """
        Sleeps the thread for ``length`` time.

        Parameters
        ----------
        length: int
            How long, in seconds, to sleep the thread for.

        Notes
        -----
        This method is only called by :meth:`~._enforce_ratelimit`. It is split
        into two functions to allow :class:`~.Loader` subclasses to overload
        just this function and easily interact with the ``length``.
        """
        self.log.info("Ratelimited, sleeping for %s seconds.", length)
        time.sleep(length)
