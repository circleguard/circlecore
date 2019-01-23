import sqlite3

from config import PATH_DB


class Cacher:
    """
    Handles compressing and caching replay data to a database.

    This class should not be instantiated because only one database connection is used, and static
    methods provide cleaner access than passing around a Cacher class.
    """

    conn = sqlite3.connect(PATH_DB)
    cursor = conn.cursor()

    def __init__(self):
        """
        This class should never be instantiated. All methods are static.
        """

        raise Exception("This class is not meant to be instantiated. Use the static methods instead")

    @staticmethod
    def cache(map_id, user_id, lzma_string, replay_id):
        """
        Writes the given lzma string to the database, linking it to the given map and user.

        Args:
            String map_id: The map id to insert into the db.
            String user_id: The user id to insert into the db.
            String lzma_string: The lzma_string to insert into the db.
            String replay_id: The id of the replay, which changes when a user overwrites their score.
        """

        compressed_string = Cacher.compress(lzma_string)
        Cacher.write("INSERT INTO replays VALUES(?, ?, ?, ?)", [map_id, user_id, compressed_string, replay_id])

    @staticmethod
    def revalidate():
        """
        Clears the cache of replays that are no longer in the top 100 for that map,
        and redownloads the replay if the user has overwritten their score since it was cached.
        // TODO: use replay_id to check for changes
        """

        return



    @staticmethod
    def check_cache(map_id, user_id):
        """
        Checks if a replay exists on the given map_id by the given user_id, and returns the lzma string if so.

        Args:
            String map_id: The map_id to check in combination with the user_id
            String user_id: The user_id to check in combination with the user_id

        Returns:
            The lzma bytestring that would have been returned by decoding the base64 api response, or None if it wasn't cached.
        """

        result = Cacher.cursor.execute("SELECT replay_data FROM replays WHERE map_id=? AND user_id=?", [map_id, user_id]).fetchone()
        return result[0] if result else None



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
    def compress(lzma_string):
        """
        Compresses the lzma string to a smaller format to store in the database.

        Args:
            String lzma_string: The lzma bytestring, returned by the api for replays, to compress

        Returns:
            A compressed bytestring from the given bytestring
        """
        return lzma_string
