from .replay import Replay

class OnlineReplay(Replay):
    """
    A Replay created from api responses.

    See Also:
        Replay
        LocalReplay
    """

    def __init__(self, replay_data, user_info):
        """
        Initializes an OnlineReplay instance.

        Unless you know what you're doing, don't call this method manually -
        this is intented to be called internally by Loader#replay_from_map.
        """

        self.replay_id = user_info.replay_id

        Replay.__init__(self, replay_data, user_info.username, user_info.enabled_mods)
