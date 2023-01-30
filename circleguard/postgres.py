import logging

import wtc
from ossapi import Ossapi
try:
    import psycopg2
except ImportError:
    raise ImportError("psycopg2 must be installed to use PostgresLoader")

from circleguard.loader import Loader
from circleguard.utils import TRACE
from circleguard.circleguard import Circleguard


class PostgresCircleguard(Circleguard):
    """
    A postgres variant of the default sqlite-backed circleguard.
    """
    def __init__(self, key, db_username, db_password, db_host, db_port, db_name,
        write_to_cache=True, slider_dir=None
    ):
        loader = PostgresLoader(key, db_username, db_password, db_host, db_port,
            db_name, write_to_cache)
        super().__init__(key, loader=loader, slider_dir=slider_dir)

class PostgresLoader(Loader):
    """
    A postgres variant of the default sqlite-backed loader.
    """
    def __init__(
        self, key, db_username, db_password, db_host, db_port, db_name,
        write_to_cache=True
    ):
        self.api = Ossapi(key)
        self.log = logging.getLogger(__name__)

        self._conn = None
        self._cursor = None
        self.write_to_cache = write_to_cache
        self.read_from_cache = True

        self._conn = psycopg2.connect(
            user=db_username,
            password=db_password,
            host=db_host,
            port=db_port,
            database=db_name
        )
        self._cursor = self._conn.cursor()

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
        self._cursor.execute("SELECT replay_data FROM replays WHERE "
            "replay_id= %s", [replay_id])
        result = self._cursor.fetchone()
        if result:
            self.log.debug("Loading replay for replay info %s from cache",
                replay_info)
            return wtc.decompress(result[0], decompressed_lzma=True)
        self.log.log(TRACE, "No replay found in cache")

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
        self._cursor.execute("INSERT INTO replays VALUES(%s, %s, %s, %s, %s)",
            [replay_id, beatmap_id, user_id, compressed_bytes, mods])
        self._conn.commit()
