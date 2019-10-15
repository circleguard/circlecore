import circleguard.utils as utils
from circleguard.enums import Mod

class UserInfo():
    """
    A container class, holding a user's map id, user id, username, replay id, enabled mods, and replay availability for a given replay.
    """

    def __init__(self, timestamp, map_id, user_id, username, replay_id, mods, replay_available):
        """
        Initializes a UserInfo class.

        Args:
            Datetime timestamp: When this replay was set.
            Integer map_id: The id of the map the replay was made on.
            Integer user_id: The id of the player who set the replay.
            String username: The username of the player who set the replay.
            Integer replay_id: The id of the replay.
            ModCombination mods: The mod combination of the mods set on the replay.
            Boolean replay_available: Whether this replay is available from the api or not.
        """

        self.timestamp = timestamp
        self.map_id = map_id
        self.user_id = user_id
        self.username = username
        self.replay_id = replay_id
        self.mods = mods
        self.replay_available = replay_available
