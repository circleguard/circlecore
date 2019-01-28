import sqlite3

import wtc

from loader import Loader
from config import PATH_DB

class Cacher:
    """
    Handles compressing and caching replay data to a database.

    This class should not be instantiated because only one database connection is used, and static
    methods provide cleaner access than passing around a Cacher class.
    """

    conn = sqlite3.connect(str(PATH_DB))
    cursor = conn.cursor()

    def __init__(self):
        """
        This class should never be instantiated. All methods are static.
        """

        raise Exception("This class is not meant to be instantiated. Use the static methods instead")

    @staticmethod
    def cache(map_id, user_id, lzma_bytes, replay_id):
        """
        Writes the given lzma bytes to the database, linking it to the given map and user.
        If an entry with the given map_id and user_id already exists, it is overwritten with
        the given lzma_bytes (after compression) and replay_id.

        The lzma string is compressed with wtc compression. See Cacher.compress and wtc.compress for more.

        Args:
            String map_id: The map id to insert into the db.
            String user_id: The user id to insert into the db.
            Bytes lzma_bytes: The lzma bytes to compress and insert into the db.
            String replay_id: The id of the replay, which changes when a user overwrites their score.
        """

        compressed_bytes = Cacher.compress(lzma_bytes)
        result = Cacher.cursor.execute("SELECT COUNT(1) FROM replays WHERE map_id=? AND user_id=?", [map_id, user_id]).fetchone()[0]
        if(result): # already exists so we overwrite (this happens when we call Cacher.revalidate)
            Cacher.write("UPDATE replays SET replay_data=?, replay_id=? WHERE map_id=? AND user_id=?", [compressed_bytes, replay_id, map_id, user_id])
        else: # else just insert
            Cacher.write("INSERT INTO replays VALUES(?, ?, ?, ?)", [map_id, user_id, compressed_bytes, replay_id])

    @staticmethod
    def revalidate(map_id, user_to_replay):
        """
        Re-caches a stored replay if one of the given users has overwritten their score on the given map since it was cached.

        Args:
            String map_id: The map to revalidate.
            Dictionary user_to_replay: The up tp date mapping of user_id to replay_id to revalidate.
        """

        result = Cacher.cursor.execute("SELECT user_id, replay_id FROM replays WHERE map_id=?", [map_id]).fetchall()
        for user_id, local_replay_id in result:
            online_replay_id = user_to_replay[user_id]
            if(local_replay_id != online_replay_id): # local (outdated) id does not match online (updated) id
                print("replay outdated, redownloading...", end="")
                Cacher.cache(map_id, user_id, Loader.replay_data(map_id, user_id), online_replay_id)
                print("cached")

    @staticmethod
    def check_cache(map_id, user_id):
        """
        Checks if a replay exists on the given map_id by the given user_id, and returns the decompressed wtc (equivelant to an lzma) string if so.

        Args:
            String map_id: The map_id to check in combination with the user_id.
            String user_id: The user_id to check in combination with the user_id.

        Returns:
            The lzma bytes that would have been returned by decoding the base64 api response, or None if it wasn't cached.
        """

        result = Cacher.cursor.execute("SELECT replay_data FROM replays WHERE map_id=? AND user_id=?", [map_id, user_id]).fetchone()
        return wtc.decompress(result[0]) if result else None



    @staticmethod
    def write(statement, args):
        """
        Writes an sql statement with the given args to the databse.

        Args:
            String statement: The prepared sql statement to execute.
            List args: The values to insert into the prepared sql statement.
                       Must be of length equal to the number of missing values in the statement.
        """

        Cacher.cursor.execute(statement, args)
        Cacher.conn.commit()

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
