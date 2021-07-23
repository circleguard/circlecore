import sqlite3
import logging
import os

import wtc

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
        self.log.info("Cacher initialized at path %s, should cache? %s ",
            path, cache)
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
        lzma_bytes: str
            The lzma stream to compress and insert into the db.
        replay_info: :class:`~circleguard.loader.ReplayInfo`
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

        beatmap_id = replay_info.beatmap_id
        user_id = replay_info.user_id
        mods = replay_info.mods.value
        replay_id = replay_info.replay_id

        self.log.log(TRACE, "Writing compressed lzma to db")
        self._write("INSERT INTO replays VALUES(?, ?, ?, ?, ?)",
            [beatmap_id, user_id, compressed_bytes, replay_id, mods])

    def check_cache(self, replay_info):
        """
        Checks the cache for a replay matching ``replay_info``, returning its
        (uncompressed) replay data if it finds a match, and ``None`` otherwise.

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

        replay_id = replay_info.replay_id

        self.log.log(TRACE, "Checking cache for replay info %s", replay_info)
        result = self.cursor.execute("SELECT replay_data FROM replays WHERE "
            "replay_id=?", [replay_id]).fetchone()
        if result:
            self.log.debug("Loading replay for replay info %s from cache",
                replay_info)
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
        # create dir if nonexistent
        if not os.path.exists(os.path.split(path)[0]):
            os.makedirs(os.path.split(path)[0])
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
