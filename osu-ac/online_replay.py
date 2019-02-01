import base64

import osrparse

from loader import Loader
from replay import Replay
from cacher import Cacher


def check_cache(function):
    """
    Decorator that checks if the replay by the given user_id on the given map_id is already cached.
    If so, returns a Replay instance from the cached string instead of requesting it from the api.

    Note that cacher, map_id, user_id, and enabled_mods must be the first, second, third, and fifth arguments to the function respectively.

    Returns:
        A Replay instance from the cached replay if it was cached, or the return value of the function if not.
    """

    def wrapper(*args, **kwargs):
        cacher = args[0]
        map_id = args[1]
        user_id = args[2]
        enabled_mods = args[4]
        lzma = cacher.check_cache(map_id, user_id)
        if(lzma):
            replay_data = osrparse.parse_replay(lzma, pure_lzma=True).play_data
            return Replay(replay_data, user_id, enabled_mods)
        else:
            return function(*args, **kwargs)
    return wrapper

class OnlineReplay(Replay):
    """
    A Replay created from api responses.

    See Also:
        Replay
        LocalReplay
    """

    def __init__(self, replay_data, player_name, enabled_mods, replay_id):
        """
        Initializes an OnlineReplay instance.

        Unless you know what you're doing, don't call this method manually -
        this is intented to be called internally by OnlineReplay.from_map.
        """

        Replay.__init__(self, replay_data, player_name, enabled_mods, replay_id)

    @staticmethod
    def from_user_info(cacher, map_id, user_info):
        """
        Creates a list of Replay instances for the users listed in user_info on the given map.

        Args:
            Cacher cacher: A cacher object containing a database connection.
            String map_id: The map_id to download the replays from.
            Dictionary user_info: A dict mapping user_ids to a list containing [username, replay_id, enabled mods] on the given map.
                                  See Loader.users_info

        Returns:
            A list of Replay instances from the given information, with entries with no replay data available excluded.
        """

        replays = [OnlineReplay.from_map(cacher, map_id, user_id, replay_info[0], replay_info[1], replay_info[2]) for user_id, replay_info in user_info.items()]
        return replays

    @staticmethod
    @check_cache
    def from_map(cacher, map_id, user_id, username, replay_id, enabled_mods):
        """
        Creates a Replay instance from a replay by the given user on the given map.

        Args:
            Cacher cacher: A cacher object containing a database connection.
            String map_id: The map_id to download the replay from.
            String user_id: The user id to download the replay of.
                            Also used as the username of the Replay.
            String replay_id: The id of the replay we are retrieving (used to cache).
            Integer enabled_mods: The base10 number representing the enabled mods

        Returns:
            The Replay instance created with the given information, or None if the replay was not available.
        """

        lzma_bytes = Loader.replay_data(map_id, user_id)
        if(lzma_bytes is None):
            return None
        parsed_replay = osrparse.parse_replay(lzma_bytes, pure_lzma=True)
        replay_data = parsed_replay.play_data
        cacher.cache(map_id, user_id, lzma_bytes, replay_id)
        return OnlineReplay(replay_data, username, enabled_mods, replay_id)
