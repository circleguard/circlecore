from circleguard.replay import Replay
class Result():
    """
    Result objects are returned from circleguard#run, and contain the two Replay objects that
    were compared, among other statistics about the comparison. Replay data can be accessed
    through the replay1 and replay2 objects.

    Attributes:
        Replay replay1: The first replay that was compared against the second.
        Replay replay2: The second replay that was compared against the first.
        Integer similarity: How similar the two replays are. This number should not directly
                        be linked to any particular meaning, such as average distance between
                        the two cursors, but lower numbers will always mean the replays are
                        more direct steals of each other.
        Boolean ischeat: Whether similarity is less than the threshold set for this comparison (usually the
                     threshold set in the config, but not if it was overriden for the specific comparison)
        String later_name: A string representation of the player who made the replay that was set later
                       (meaning, if it was stolen, it was almost certainly stolen from the other replay in
                       the comparison). This will usually be the username of the player, but it takes the
                       value of whatever is stored in the replay's username field. See the Replay
                       documentation for more information on what values could be stored in this field.
    """

    def __init__(self, replay1: Replay, replay2: Replay, similarity: int, ischeat: bool, later_name: str):
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
            String later_name: A string representation of the player who made the replay that was set later
                       (meaning, if it was stolen, it was almost certainly stolen from the other replay in
                       the comparison). This will usually be the username of the player, but it takes the
                       value of whatever is stored in the replay's username field. See the Replay
                       documentation for more information on what values could be stored in this field.
        """

        self.replay1: Replay = replay1
        self.replay2: Replay = replay2
        self.similarity: int = similarity
        self.ischeat: bool = ischeat
        self.later_name: str = later_name
