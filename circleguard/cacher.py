import sqlite3
import logging
import os

import wtc

from circleguard.loader import Loader
from circleguard.exceptions import CircleguardException
from circleguard.utils import TRACE

class Cacher:
    """
    Handles compressing and caching replay data to a database.

    Parameters
    ----------
    cache: bool
        Whether or not replays should be cached.
    path: str or :class:`os.PathLike`
        The absolute path to the database. If the path does not exist,
        a fresh database will be created there.

    Notes
    -----
    Each Cacher instance maintains its own database connection.
    """
    def __init__(self, cache, path):

        self.log = logging.getLogger(__name__)
        self.should_cache = cache
        if not os.path.isfile(str(path)):
            self._create_cache(str(path))
        self.conn = sqlite3.connect(str(path))
        self.cursor = self.conn.cursor()

    def cache(self, lzma_bytes, replay_info):
        """
        Caches a replay in the form of a (compressed) lzma stream to the
        database, linking it to the replay info.

        Parameters
        ----------
        map_id: str
            The map id to insert into the db.
        lzma_bytes: str
            The lzma stream to compress and insert into the db.
        replay_info: :class:`~circleguard.replay_info.ReplayInfo`
            The ReplayInfo object representing this replay.

        Notes
        -----
        If an entry with the given replay info already exists, it is overwritten
        by the passed lzma.

        The lzma string is compressed with wtc compression. See
        :func:`~Cacher._compress` and :func:`wtc.compress` for more.

        A call to this method has no effect if the Cacher's ``should_cache``
        is ``False``.
        """

        self.log.debug("Caching lzma bytes")

        if self.should_cache is False:
            self.log.debug("Cacher should_cache is False, not caching")
            return

        compressed_bytes = self._compress(lzma_bytes)

        map_id = replay_info.map_id
        user_id = replay_info.user_id
        mods = replay_info.mods.value
        replay_id = replay_info.replay_id

        result = self.cursor.execute("SELECT COUNT(1) FROM replays WHERE map_id=? AND user_id=? AND mods=?", [map_id, user_id, mods]).fetchone()[0]
        self.log.log(TRACE, "Writing compressed lzma to db")
        if result: # already exists so we overwrite (this happens when we call Cacher.revalidate)
            self._write("UPDATE replays SET replay_data=?, replay_id=? WHERE map_id=? AND user_id=? AND mods=?", [compressed_bytes, replay_id, map_id, user_id, mods])
        else: # else just insert
            self._write("INSERT INTO replays VALUES(?, ?, ?, ?, ?)", [map_id, user_id, compressed_bytes, replay_id, mods])

    def revalidate(self, loader, replay_info):
        """
        Checks entries in ``replay_info`` against their entries in the database
        (if any) to look for score id mismatches, indicating an outdated replay.
        If there are mismatches, the replay is redownloaded and cached from the
        replay info.

        Parameters
        ----------
        loader: :class:`~circleguard.loader.Loader`
            The Loader from the circleguard instance to redownload replays with
            if they are outdated.
        replay_info: list[:class:`~circleguard.replay_info.ReplayInfo`]
            A list of ReplayInfo objects containing the up-to-date information
            of user's replays.

        Raises
        ------
        CircleguardException
            Raised when the redownloaded replay id is lower than the cached
            replay id. This should never happen and is indicative of either a
            fault on our end or the api's end.

            Also raised if the replay data is not available from the api when
            redownloaded.

        Notes
        -----
        If the replay is found to be outdated, it will be overwritten
        by the newer replay in the database.
        """
        self.log.info("Revalidating cache with %d replay_infos", len(replay_info))

        for info in replay_info:
            map_id = info.map_id
            user_id = info.user_id
            mods = info.enabled_mods.value

            self.log.log(TRACE, "Revalidating entry with map id %s, user %d, mods %s", map_id, user_id, mods)

            result = self.cursor.execute("SELECT replay_id FROM replays WHERE map_id=? AND user_id=? AND mods=?", [map_id, user_id, mods]).fetchall()
            if not result:
                self.log.trace("Nothing cached with map id %s, user %d, mods %s", map_id, user_id, mods)
                continue # nothing cached

            db_replay_id = result[0][0] # blame sqlite for nesting tuples in lists
            new_replay_id = info.replay_id

            if db_replay_id != new_replay_id:
                if db_replay_id > new_replay_id:
                    raise CircleguardException("The cached replay id of {} is higher than the new replay id of {}. Map id: {}, User id: {}, mods: {}"
                                                .format(db_replay_id, new_replay_id, user_id, map_id, mods))

                self.log.info("Cached replay on map %d by user %d with mods %d is outdated, redownloading", map_id, user_id, mods)
                lzma_data = loader.replay_data(info)
                if lzma_data is None:
                    raise CircleguardException("We could not load lzma data for map {}, user {}, mods {}, replay available {} while revalidating."
                                                .format(map_id, user_id, mods, info.replay_available))
                self.cache(lzma_data, info)

    def check_cache(self, map_id, user_id, mods):
        """
        Checks the cache for a replay described by the parameters, and returns
        its data if the cache contains the replay.

        Parameters
        ----------
        map_id: int
            The id of the map the replay was played on.
        user_id: int
            The id of the user that played the replay.
        mods: :class:`~circleguard.mod.ModCombination`
            The mods this replay was played with.

        Returns
        -------
        str or None
            The replay data in decompressed lzma form if the cache contains the
            replay, or None if not.
        """
        mods = mods.value
        self.log.log(TRACE, "Checking cache for a replay on map %d by user %d with mods %s", map_id, user_id, mods)
        result = self.cursor.execute("SELECT replay_data FROM replays WHERE map_id=? AND user_id=? AND mods=?", [map_id, user_id, mods]).fetchone()
        if result:
            self.log.debug("Loading replay on map %d by user %d with mods %s from cache", map_id, user_id, mods)
            return wtc.decompress(result[0], decompressed_lzma=True)
        self.log.log(TRACE, "No replay found in cache")
        return None

    def _write(self, statement, args):
        """
        A helper method that writes an sql statement with
        the given args, and commits the connection.

        Parameters
        ----------
        statement: str
            The sql statement to execute.
        args: list
            The values to insert into the statement.
            Must be of length equal to the number of missing values
            (question marks) in the statement.
        """
        self.cursor.execute(statement, args)
        self.conn.commit()

    def _compress(self, lzma_bytes):
        """
        Compresses an lzma string with wtc compression
        (see :func:`wtc.compress`).

        Parameters
        ----------
        lzma_bytes: str
            The lzma string representing a replay, to compress.

        Returns
        -------
        str
            The lzma_bytes string, compressed with wtc compression
            (:func:`wtc.compress`).

        Notes
        -----
        wtc compression is not lossless, in order to save space. Please see
        :func:`wtc.compress` for more details.
        """
        self.log.log(TRACE, "Compressing lzma bytes")
        return wtc.compress(lzma_bytes)

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
        if not os.path.exists(os.path.split(path)[0]): # create dir if nonexistent
            os.makedirs(os.path.split(path)[0])
        conn = sqlite3.connect(str(path))
        c = conn.cursor()
        c.execute("""CREATE TABLE "REPLAYS"(
            "MAP_ID" INTEGER NOT NULL,
            "USER_ID" INTEGER NOT NULL,
            "REPLAY_DATA" MEDIUMTEXT NOT NULL,
            "REPLAY_ID" INTEGER NOT NULL,
            "MODS" INTEGER NOT NULL,
            PRIMARY KEY("REPLAY_ID")
        )""")
        conn.close()
