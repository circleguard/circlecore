from circleguard.replay import Replay
class Result():
    """
    Result objects are returned from circleguard#run, and contain the two Replay objects that
    were compared, among other statistics about the comparison. Replay data can be accessed
    through the replay1 and replay2 objects.

    Attributes:
        Replay replay1: The first replay that was compared against the second.
        Replay replay2: The second replay that was compared against the first.
        Replay earlier_replay: The earlier of the two replays (when the score was made). This is a
                               reference to either replay1 or replay2.
        Replay later_replay: The later of the two replays (when the score was made). This is a
                             reference to either replay1 or replay2.
        Integer similarity: How similar the two replays are. This number should not directly
                        be linked to any particular meaning, such as average distance between
                        the two cursors, but lower numbers will always mean the replays are
                        more direct steals of each other.
        Boolean ischeat: Whether similarity is less than the threshold set for this comparison (usually the
                     threshold set in the config, but not if it was overriden for the specific comparison)
    """

    def __init__(self, replay1: Replay, replay2: Replay, similarity: int, ischeat: bool):
        """
        Initializes a Result instance.

        This method is for internal use only. Unless you know what you're doing, you should only ever
        receive this object from calling circleguard method, and not create it yourself.

        Args:
            Replay replay1: The first replay that was compared against the second.
            Replay replay2: The second replay that was compared against the first.
            Integer similarity: How similar the two replays are. This number should not directly
                        be linked to any particular meaning, such as average distance between
                        the two cursors, but lower numbers will always mean the replays are
                        more direct steals of each other.
            Boolean ischeat: Whether similarity is less than the threshold set for this comparison
                        (usually the threshold set in the config, but not if it was overriden for
                        the specific comparison)
        """

        self.replay1: Replay = replay1
        self.replay2: Replay = replay2
        self.similarity: int = similarity
        self.ischeat: bool = ischeat

        if self.replay1.timestamp < self.replay2.timestamp:
            self.earlier_replay: Replay = self.replay1
            self.later_replay: Replay = self.replay2
        else:
            self.earlier_replay: Replay = self.replay2
            self.later_replay: Replay = self.replay1
