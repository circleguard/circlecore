import osrparse

from replay import Replay

class LocalReplay(Replay):
    """
    A replay created from a local .osr file.

    See Also:
        Replay
        OnlineReplay
    """

    def __init__(self, replay_data, player_name, enabled_mods):
        """
        Initializes a LocalReplay instance.

        Unless you know what you're doing, don't call this method manually -
        this is intented to be called internally by LocalReplay.from_path.

        Args:
            List replay_data: A list of osrpasrse.ReplayEvent objects, containing
                              x, y, time_since_previous_action, and keys_pressed.
            String player_name: An identifier marking the player that did the replay. Name or user id are common.
            Integer enabled_mods: A base10 representation of the enabled mods on the replay.
        """

        self.replay_id = None

        Replay.__init__(self, replay_data, player_name, enabled_mods)

    @staticmethod
    def from_path(path):
        """
        Creates a Replay instance from the data contained by file at the given path.

        Args:
            [String or Path] path: The absolute path to the replay file.

        Returns:
            The Replay instance created from the given path.
        """

        parsed_replay = osrparse.parse_replay_file(path)
        check_replay_data = parsed_replay.play_data
        enabled_mods = parsed_replay.mod_combination
        player_name = parsed_replay.player_name

        return LocalReplay(check_replay_data, player_name, enabled_mods)
