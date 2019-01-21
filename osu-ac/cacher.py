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
    def cache(map_id, user_id, lzma_string):
        """
        Writes the given lzma string to the database, linking it to the given map and user.

        Args:
            String map_id: The map id to insert into the db.
            String user_id: The user id to insert into the db.
            String lzma_string: The lzma_string to insert into the db.
        """

        compressed_string = Cacher.compress(lzma_string)
        Cacher.write("INSERT INTO replays VALUES(?, ?, ?)", [map_id, user_id, compressed_string])

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
