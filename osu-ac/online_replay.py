import requests
import base64

import osrparse

from loader import Loader
from replay import Replay
from cacher import Cacher


def check_cache(function):
    """
    Decorator that checks if the replay by the given user_id on the given map_id is already cached.
    If so, returns a Replay instance from the cached string instead of requesting it from the api.

    Note that map_id and user_id must be the first and second arguments to the function respectively.

    Returns:
        A Replay instance from the cached replay if it was cached, or the return value of the function if not.
    """

    def wrapper(*args, **kwargs):
        map_id = args[0]
        user_id = args[1]
        lzma = Cacher.check_cache(map_id, user_id)
        if(lzma):
            replay_data = osrparse.parse_replay(lzma, pure_lzma=True).play_data
            return Replay(replay_data, user_id)
        else:
            function(*args, **kwargs)
    return wrapper

class OnlineReplay(Replay):
    """
    A Replay created from api responses.

    See Also:
        Replay
        LocalReplay
    """

    def __init__(self, replay_data, player_name):
        """
        Initializes an OnlineReplay instance.

        Unless you know what you're doing, don't call this method manually -
        this is intented to be called internally by OnlineReplay.from_map.
        """

        Replay.__init__(self, replay_data, player_name)

    @staticmethod
    @check_cache
    def from_map(map_id, user_id, cache):
        """
        Creates a Replay instance from a replay by the given user on the given map.

        Args:
            String map_id: The map_id to download the replay from.
            String user_id: The user id to download the replay of.
                            Also used as the username of the Replay.

        Returns:
            The Replay instance created with the given information.
        """

        replay_data_string = Loader.replay_data(map_id, user_id)
        # convert to bytes so the lzma can be deocded with osrparse.
        replay_data_bytes = base64.b64decode(replay_data_string)
        parsed_replay = osrparse.parse_replay(replay_data_bytes, pure_lzma=True)
        replay_data = parsed_replay.play_data
        if(cache):
            # Bytes is actually smaller than the b64 encoded string here, so we store that (TODO: compress (well) before storage)
            Cacher.cache(map_id, user_id, replay_data_bytes)
        return OnlineReplay(replay_data, user_id)
