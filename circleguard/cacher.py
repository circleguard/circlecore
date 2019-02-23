import sqlite3

import wtc

from loader import Loader
from config import PATH_DB

class Cacher:
    """
    Handles compressing and caching replay data to a database.

    Each Cacher instance maintains its own database connection.
    Be wary of instantiating too many.
    """

    def __init__(self, cache):
        """
        Initializes a Cacher instance.

        Args:
            Boolean cache: Whether replays should be cached or not.
        """

        self.should_cache = cache
        self.conn = sqlite3.connect(str(PATH_DB))
        self.cursor = self.conn.cursor()

    def cache(self, map_id, user_id, lzma_bytes, replay_id):
        """
        Writes the given lzma bytes to the database, linking it to the given map and user.
        If an entry with the given map_id and user_id already exists, it is overwritten with
        the given lzma_bytes (after compression) and replay_id.

        The lzma string is compressed with wtc compression. See Cacher.compress and wtc.compress for more.

        A call to this method has no effect if the Cacher's should_cache is False.

        Args:
            String map_id: The map id to insert into the db.
            Integer user_id: The user id to insert into the db.
            Bytes lzma_bytes: The lzma bytes to compress and insert into the db.
            Integer replay_id: The id of the replay, which changes when a user overwrites their score.
        """

        if(not self.should_cache):
            return
        print("caching...", end="", flush=True)
        compressed_bytes = Cacher.compress(lzma_bytes)
        result = self.cursor.execute("SELECT COUNT(1) FROM replays WHERE map_id=? AND user_id=?", [map_id, user_id]).fetchone()[0]
        if(result): # already exists so we overwrite (this happens when we call Cacher.revalidate)
            self.write("UPDATE replays SET replay_data=?, replay_id=? WHERE map_id=? AND user_id=?", [compressed_bytes, replay_id, map_id, user_id])
        else: # else just insert
            self.write("INSERT INTO replays VALUES(?, ?, ?, ?)", [map_id, user_id, compressed_bytes, replay_id])
        print("done")

    def revalidate(self, map_id, user_info, loader):
        """
        Re-caches a stored replay if one of the given users has overwritten their score on the given map since it was cached.

        Args:
            String map_id: The map to revalidate.
            Dictionary user_info: The up to date mapping of user_id to [username, replay_id, enabled_mods] to revalidate.
                                       Only contains information for a single map.
            Loader loader: The Loader from the circleguard instance to redownload beatmaps with if they are outdated.
        """

        result = self.cursor.execute("SELECT user_id, replay_id FROM replays WHERE map_id=?", [map_id]).fetchall()

        # filter result to only contain entries also in user_info
        result = [info for info in result if info[0] in user_info.keys()]
        for user_id, local_replay_id in result:
            online_replay_id = user_info[user_id][1]
            if(local_replay_id != online_replay_id): # local (outdated) id does not match online (updated) id
                print("replay by {} on {} outdated, redownloading...".format(user_id, map_id), end="")
                # this **could** conceivable be the source of a logic error by Loader.replay_data returning None and the cache storing None,
                # but since we only re-cache when we already stored a replay by them their future replay shouldn't ever be unavailable.
                # We don't even know why some replays are unavailable though, so it's possible.
                self.cache(map_id, user_id, loader.replay_data(map_id, user_id), online_replay_id)
                print("cached")

    def check_cache(self, map_id, user_id):
        """
        Checks if a replay exists on the given map_id by the given user_id, and returns the decompressed wtc (equivelant to an lzma) string if so.

        Args:
            String map_id: The map_id to check in combination with the user_id.
            String user_id: The user_id to check in combination with the user_id.

        Returns:
            The lzma bytes that would have been returned by decoding the base64 api response, or None if it wasn't cached.
        """

        result = self.cursor.execute("SELECT replay_data FROM replays WHERE map_id=? AND user_id=?", [map_id, user_id]).fetchone()
        if(result):
            print("Loading replay by {} from cache".format(user_id))
            return wtc.decompress(result[0])

        return None

    def write(self, statement, args):
        """
        Writes an sql statement with the given args to the databse.

        Args:
            String statement: The prepared sql statement to execute.
            List args: The values to insert into the prepared sql statement.
                       Must be of length equal to the number of missing values in the statement.
        """

        self.cursor.execute(statement, args)
        self.conn.commit()


    @staticmethod
    def compress(lzma_bytes):
        """
        Compresses the lzma string to a (smaller) wtc string to store in the database.

        Args:
            Bytes lzma_bytes: The lzma bytes, returned by the api for replays, to compress.

        Returns:
            A compressed bytes from the given bytes, using lossy wtc compression.
        """

        return wtc.compress(lzma_bytes)
