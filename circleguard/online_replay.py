from replay import Replay

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

        self.replay_id = replay_id

        Replay.__init__(self, replay_data, player_name, enabled_mods)
