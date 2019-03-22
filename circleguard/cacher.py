import sqlite3

import wtc

from circleguard.loader import Loader
from circleguard.exceptions import CircleguardException

class Cacher:
    """
    Handles compressing and caching replay data to a database.

    Each Cacher instance maintains its own database connection.
    Be wary of instantiating too many.
    """

    def __init__(self, cache, path):
        """
        Initializes a Cacher instance.

        Args:
            Boolean cache: Whether replays should be cached or not.
            Path path: A pathlike object representing the absolute path to the database
        """

        self.should_cache = cache
        self.conn = sqlite3.connect(str(path))
        self.cursor = self.conn.cursor()

    def cache(self, lzma_bytes, user_info):
        """
        Writes the given lzma bytes to the database, linking it to the given map and user.
        If an entry with the given map_id and user_id already exists, it is overwritten with
        the given lzma_bytes (after compression) and replay_id.

        The lzma string is compressed with wtc compression. See Cacher.compress and wtc.compress for more.

        A call to this method has no effect if the Cacher's should_cache is False.

        Args:
            String map_id: The map id to insert into the db.
            Bytes lzma_bytes: The lzma bytes to compress and insert into the db.
            UserInfo user_info: The UserInfo object representing this replay.
        """

        if(not self.should_cache):
            return
        print("caching...", end="", flush=True)
        compressed_bytes = Cacher.compress(lzma_bytes)

        map_id = user_info.map_id
        user_id = user_info.user_id
        mods = user_info.mods
        replay_id = user_info.replay_id

        result = self.cursor.execute("SELECT COUNT(1) FROM replays WHERE map_id=? AND user_id=? AND mods=?", [map_id, user_id, mods]).fetchone()[0]
        if(result): # already exists so we overwrite (this happens when we call Cacher.revalidate)
            self.write("UPDATE replays SET replay_data=?, replay_id=? WHERE map_id=? AND user_id=? AND mods=?", [compressed_bytes, replay_id, map_id, user_id, mods])
        else: # else just insert
            self.write("INSERT INTO replays VALUES(?, ?, ?, ?, ?)", [map_id, user_id, compressed_bytes, replay_id, mods])
        print("done")

    def revalidate(self, loader, user_info):
        """
        Revalidates every entry in user_info, which may contain different maps or users. If an entry exists in the cache with a UserInfo's
        map_id, user_id, and enabled_mods, the score is redownloaded and the outdated score is replaced with the new one in the cache.

        Args:
            Loader loader: The Loader from the circleguard instance to redownload beatmaps with if they are outdated.
            List [UserInfo]: A list of UserInfo objects containing the up-to-date information of user's replays.
        """

        print("revalidating relevant scores in cache")

        for info in user_info:
            map_id = info.map_id
            user_id = info.user_id
            mods = info.enabled_mods

            result = self.cursor.execute("SELECT replay_id FROM replays WHERE map_id=? AND user_id=? AND mods=?", [map_id, user_id, mods]).fetchall()
            if(not result):
                continue # nothing cached

            db_replay_id = result[0][0] # blame sqlite for nesting tuples in lists
            new_replay_id = info.replay_id

            if(db_replay_id != new_replay_id):
                if(db_replay_id > new_replay_id):
                    raise CircleguardException("The cached replay id of {} is higher than the new replay id of {}. Map id: {}, User id: {}, mods: {}"
                                                .format(db_replay_id, new_replay_id, user_id, map_id, mods))

                print("replay by {} on {} with mods {} outdated, redownloading..".format(user_id, map_id, mods), end="")
                lzma_data = loader.replay_data(info)
                if(lzma_data is None):
                    raise CircleguardException("We could not load lzma data for map {}, user {}, mods {}, replay available {} while revalidating."
                                                .format(map_id, user_id, mods, info.replay_available))
                self.cache(lzma_data, info)

        print("done revalidating")
    def check_cache(self, map_id, user_id, mods):
        """
        Checks if a replay exists on the given map_id by the given user_id with the given mods, and returns the decompressed wtc (equivelant to an lzma) string if so.

        Args:
            String map_id: The map_id to check for.
            String user_id: The user_id to check for.
            Integer mods: The bitwise enabled mods for the play.

        Returns:
            The lzma bytes that would have been returned by decoding the base64 api response, or None if it wasn't cached.
        """

        result = self.cursor.execute("SELECT replay_data FROM replays WHERE map_id=? AND user_id=? AND mods=?", [map_id, user_id, mods]).fetchone()
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
