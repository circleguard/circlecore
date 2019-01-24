import sqlite3

from config import PATH_DB

import struct
import lzma

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
        packed_osr = Cacher.pack_osr(compressed_string)
        Cacher.write("INSERT INTO replays VALUES(?, ?, ?, ?)", [map_id, user_id, packed_osr, replay_id])

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
        return Cacher.unpack_osr(result[0]) if result else None



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

    @staticmethod
    def __PackInt24(integer):
        """
        Converts an integer to a 24 bit bytes object.

        Args:
            int integer: The number to be converted

        Returns:
            A 24 bit int as bytes
        """
        if integer not in range(-0x800000, 0x800000):
            raise ValueError('Value must be between -0x800000 and 0x800000')
        output = struct.pack('<i', integer)
        output = output[:-1]
        return output

    @staticmethod
    def __UnpackInt24(intbytes):
        """
        Converts a 24 bit bytes object to an integer.

        Args:
            bytes intbytes: The bytes to convert to int

        Returns:
            An integer representation of the input
        """
        if len(intbytes) != 3:
            raise ValueError('Value must be an int24')
        sign = intbytes[-1] & 0x80
        if sign:
            intbytes = intbytes + b'\xFF'
        else:
            intbytes = intbytes + b'\x00'
        return struct.unpack('<i', intbytes)[0]

    @staticmethod
    def pack_osr(lzma_stream):
        """
        Packs replay into a more compact format

        Args:
            bytes lzma_stream: lzma stream from a replay

        Returns:
            An lzma compressed bytestring
        """
        text = lzma.decompress(lzma_stream).decode('UTF-8')
        raw = b''
        for frame in text.split(','):
            if not frame:
                continue
            w, x, y, z = frame.split('|')
            w = int(w)
            x = float(x)
            y = float(y)
            z = int(z)

            #Everything we need from Z is in the first byte
            z = z & 0xFF

            #To fit x and y into shorts, they can be scaled to retain more precision.
            x = int(round(x * 16))
            y = int(round(y * 16))


            #Prevent the coordinates from being too large for a short. If this happens, the cursor is way offscreen anyway.
            if x <= -0x8000: x = -0x8000
            elif x >= 0x7FFF: x = 0x7FFF
            if y <= -0x8000: y = -0x8000
            elif y >= 0x7FFF: y = 0x7FFF
            

            #w: signed 24bit integer
            #x: signed short
            #y: signed short
            #z: unsigned char
            raw += Cacher.__PackInt24(w) + struct.pack('<hhB', x, y, z)

            
        compressed = lzma.compress(raw, format=2)
        return compressed

    @staticmethod
    def unpack_osr(encoded_data):
        """
        Unpacks replay data into the more familiar replay format

        Args:
            bytes encoded_data: Packed replay data from pack_osr

        Returns:
            An lzma compressed bytestring (Just like the one used in normal OSRs)
        """
        output = ''
        data = lzma.decompress(encoded_data)
        #each frame is 8 bytes
        for i in range(0, len(data), 8):
            frame = data[i : i+8]
            #extract W on its own since it's an int24 and cannot be used with struct.unpack
            b_w, frame = frame[:3], frame[3:]
            
            #w: signed 24bit integer
            w = Cacher.__UnpackInt24(b_w)

            #x: signed short
            #y: signed short
            #z: unsigned char
            x, y, z = struct.unpack('<hhB', frame)

            #X and Y are stored as shorts; convert and scale them back to their float forms
            x /= 16
            y /= 16
            
            output += f'{w}|{x}|{y}|{z},'
        lzma_stream = lzma.compress(output.encode('UTF-8'), format=2)
        return lzma_stream
