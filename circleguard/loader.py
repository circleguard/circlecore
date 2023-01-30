import base64
import logging
from lzma import LZMAError
from functools import lru_cache
from pathlib import Path
import sqlite3
import wtc

import osrparse
from ossapi import Ossapi, ReplayUnavailableException

from circleguard.utils import TRACE
from circleguard.span import Span


class NoInfoAvailableException(Exception):
    def __init__(self):
        super().__init__("No info was available from the api for the given "
            "arguments.")

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

        decompressed_lzma = self._check_cache(replay_info)
        if not decompressed_lzma:
            return function(*args, **kwargs)

        return osrparse.parse_replay_data(decompressed_lzma, decompressed=True)
    return wrapper



class Loader:
    """
    Manages interactions with the osu api, using the :mod:`ossapi` wrapper.

    Parameters
    ----------
    key: str
        A valid api key. Can be retrieved from https://osu.ppy.sh/p/api/.
    cache_path: str
        The path to the database to use for caching. A new database will be
        created at this location if one doesn't exist already.
        |br|
        If ``None``, no cache will be used or created.

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

    def __init__(self, key, cache_path=None, write_to_cache=True):
        self.api = Ossapi(key)
        self.log = logging.getLogger(__name__)

        self._conn = None
        self._cursor = None
        self.write_to_cache = write_to_cache and bool(cache_path)
        self.read_from_cache = bool(cache_path)

        if cache_path:
            cache_path = Path(cache_path)
            if not cache_path.is_file():
                self._create_cache(cache_path)

            self._conn = sqlite3.connect(str(cache_path))
            self._cursor = self._conn.cursor()

    def replay_info(self, beatmap_id, span=None, user_id=None, mods=None, \
        limit=True):
        """
        Retrieves replay infos from a map's leaderboard.

        Parameters
        ----------
        beatmap_id: int
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
            beatmap_id, {k: locals_[k] for k in locals_ if k != 'self'})

        if not (span or user_id):
            raise ValueError("One of user_id or span must be passed, but not "
                "both")
        api_limit = None
        if span:
            api_limit = max(span)
        mods = None if mods is None else mods.value
        scores = self.api.get_scores(beatmap_id, mode=0, limit=api_limit,
            user=user_id, mods=mods)

        if scores == []:
            # The logic below allows us to load eg
            # ``Map(221777, mods=Mod.SO + Mod.PF + Mod.HT)`` or some equally
            # absurd mod combination for which there are no replays, and have
            # that loading not throw ``NoInfoAvailableException``. Instead,
            # the map's replays list will just be empty.
            # However, we only want to apply this if we're loading a map, ie
            # ``span`` has been passed. If ``user_id`` was passed instead, raise
            # the exception as usual.
            if user_id:
                raise NoInfoAvailableException()
            # the osu! api doesn't distinguish between a map not existing, and
            # no scores having been set on that map for a particular mod
            # combination - both are empty responses which will trigger a no
            # info available exception. We need to figure out which case has
            # occurred here to determine if we should raise or not.
            beatmap_response = self.api.get_beatmaps(beatmap_id=beatmap_id)
            # If the beatmap does not exist, this response will be empty.
            if not beatmap_response:
                raise NoInfoAvailableException()
            # else, the empty response is ok.

        if span:
            # important: if we iterated over ``span`` instead, we would change
            # the order of the scores returned, since ``Span`` is an (unordered)
            # set. Iterate over the scores instead, which have a guaranteed
            # order.
            scores = [score for (i, score) in enumerate(scores, 1) if i in span]

        # limit only applies if user_id was set
        return scores[0] if (limit and user_id) else scores


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

        scores = self.api.get_user_best(user_id, mode=0, limit=max(span))
        if scores == []:
            raise NoInfoAvailableException()
        if mods:
            _scores = []
            for score in scores:
                if score.mods == mods:
                    _scores.append(score)
            scores = _scores

        # remove span indices which would cause an index error because there
        # weren't that many replay infos returned by the api. eg if there
        # were 4 responses, remove any span above 4
        _span = [x for x in span if x <= len(scores)]
        scores = [scores[i-1] for i in _span]
        return scores


    def load_replay_data(self, beatmap_id, user_id, mods=None):
        """
        Retrieves replay data from the api.

        Parameters
        ----------
        beatmap_id: int
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
            "mods %s", user_id, beatmap_id, mods)
        mods = None if mods is None else mods.value
        content = self.api.get_replay(beatmap_id=beatmap_id, user=user_id,
            mods=mods, mode=0)
        return base64.b64decode(content)

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
            ``time_delta``, and ``keys``.
        None
            If no replay data was available.

        Raises
        ------
        ReplayUnavailableException
            If ``user_info.replay_available` was 1, but we did not receive
            replay data from the api.
        """

        user_id = replay_info.user_id
        beatmap_id = replay_info.beatmap_id
        mods = replay_info.mods
        if not replay_info.replay_available:
            self.log.debug("Replay data by user %d on map %d with mods %s not "
                "available", user_id, beatmap_id, mods)
            return None

        lzma_bytes = self.load_replay_data(beatmap_id, user_id, mods)
        # TODO can this ever be `None`? shouldn't the `base64.b64decode` call in
        # `self.load_replay_data` error on a `None` value? in other words, I
        # don't see how the decode function could ever return `None`.
        if lzma_bytes is None:
            raise ReplayUnavailableException("The api guaranteed there "
                "would be a replay available, but we did not receive any data.")
        try:
            replay_data = osrparse.parse_replay_data(lzma_bytes, decoded=True)
        # see https://github.com/circleguard/circlecore/issues/61
        # api sometimes returns corrupt replays
        except LZMAError:
            self.log.warning("lzma from %r could not be decompressed, api "
                "returned corrupt replay", replay_info)
            return None
        if cache:
            self._cache(lzma_bytes, replay_info)
        return replay_data

    # TODO make this check cache for the replay
    def replay_data_from_id(self, replay_id, _cache):
        """
        Retrieves replay data from the api, given a replay id.

        Parameters
        ----------
        replay_id: int
            The id of the replay to retrieve data for.
        """
        content = self.api.get_replay(score_id=replay_id)
        replay_data = osrparse.parse_replay_data(content)
        # TODO cache the replay here, might require some restructuring/double
        # checking everything will work because we only have its id, not map
        # or user id. In fact I think our db asserts map and user id are nonull
        # so insertion into old dbs probably won't work (and we'd have to change
        # the schema).
        # TODO include a db version in the db for future scenarios like this?
        # look into how that's typically done, maybe just a `VERSION` table with
        # a single row
        return replay_data

    @lru_cache()
    def beatmap_id(self, beatmap_hash):
        """
        Retrieves a beatmap id from a corresponding beatmap hash through the
        api.

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

        beatmaps = self.api.get_beatmaps(beatmap_hash=beatmap_hash)
        if beatmaps == []:
            return 0
        return beatmaps[0].beatmap_id

    # TODO remove in core 6.0.0
    map_id = beatmap_id

    @lru_cache()
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

        user = self.api.get_user(username, user_type="string")
        if user == []:
            return 0
        return user.user_id

    @lru_cache()
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
        user = self.api.get_user(user_id, user_type="id")
        if user == []:
            return ""
        return user.username

    def _create_cache(self, path):
        """
        Creates a database with the necessary tables at the given path.

        Parameters
        ----------
        path: str
            The absolute path to where the database should be created.

        Notes
        -----
        This function will create directories specified in the path if they
        don't already exist.
        """
        self.log.info("Cache not found at path %s, creating cache", path)
        # create dir if nonexistent
        import os
        if not os.path.exists(path.parent):
            os.makedirs(path.parent)
        conn = sqlite3.connect(str(path))
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE "REPLAYS" (
                `MAP_ID` INTEGER NOT NULL,
                `USER_ID` INTEGER NOT NULL,
                `REPLAY_DATA` MEDIUMTEXT NOT NULL,
                `REPLAY_ID` INTEGER NOT NULL,
                `MODS` INTEGER NOT NULL,
                PRIMARY KEY(`REPLAY_ID`)
            )""")
        # create our index - this does unfortunately add some size (and
        # insertion time) to the db, but it's worth it to get fast lookups on
        # a map, user, or mods, which are all common operations.
        c.execute(
            """
            CREATE INDEX `lookup_index` ON `REPLAYS` (
                `MAP_ID`, `USER_ID`, `MODS`
            )
            """)
        conn.close()

    def _cache(self, lzma_bytes, replay_info):
        """
        Compresses and caches the given lzma_bytes to the database, linking it
        to the given replay_info. If an entry with the given replay info already
        exists, it is overwritten.

        Parameters
        ----------
        lzma_bytes: str
            The lzma stream to compress and insert into the db.
        replay_info: :class:`~circleguard.loader.ReplayInfo`
            The ReplayInfo object representing this replay.
        """
        if not self.write_to_cache:
            return

        compressed_bytes = wtc.compress(lzma_bytes)
        beatmap_id = replay_info.beatmap_id
        user_id = replay_info.user_id
        mods = replay_info.mods.value
        replay_id = replay_info.replay_id

        self.log.log(TRACE, "Writing compressed lzma to db")
        self._cursor.execute("INSERT INTO replays VALUES(?, ?, ?, ?, ?)",
            [beatmap_id, user_id, compressed_bytes, replay_id, mods])
        self._conn.commit()

    def _check_cache(self, replay_info):
        """
        Checks the cache for a replay matching ``replay_info``.

        Parameters
        ----------
        replay_info: :class:`~circleguard.loader.ReplayInfo`
            The replay info to search for a matching replay with.

        Returns
        -------
        str or None
            The replay data in decompressed lzma form if the cache contains the
            replay, or None if not.
        """
        if not self.read_from_cache:
            return None

        replay_id = replay_info.replay_id

        self.log.log(TRACE, "Checking cache for replay info %s", replay_info)
        result = self._cursor.execute("SELECT replay_data FROM replays WHERE "
            "replay_id=?", [replay_id]).fetchone()
        if result:
            self.log.debug("Loading replay for replay info %s from cache",
                replay_info)
            return wtc.decompress(result[0], decompressed_lzma=True)
        self.log.log(TRACE, "No replay found in cache")
