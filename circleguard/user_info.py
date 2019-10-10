import circleguard.utils as utils
from circleguard.enums import Mod

class UserInfo():
    """
    A container class representing all the information needed
    to load a replay from the api.

    Parameters
    ----------
    timestamp: Datetime
        When this replay was set.
    map_id: int
        The id of the map the replay was played on.
    user_id: int
        The id of the player who played the replay.
    username: str
        The username of the player who played the replay.
    replay_id: str
        The id of the replay.
    enabled_mods: int
        The bitwise mod combination the replay was played with.
    replay_available: bool
        Whether this replay is available from the api or not.
    """
    def __init__(self, timestamp, map_id, user_id, username, replay_id, mods, replay_available):
        self.timestamp = timestamp
        self.map_id = map_id
        self.user_id = user_id
        self.username = username
        self.replay_id = replay_id
        self.mods = mods
        self.replay_available = replay_available
