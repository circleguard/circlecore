from circleguard.replay import Replay
from circleguard.enums import ResultType

# Hierarchy
#                                 Result
#          InvestigationResult             ComparisonResult
#              RelaxResult               ReplayStealingResult
#
#
class Result():
    """
    The result of a test for cheats, either on a single replay or a
    collection of replays.

    Attributes:
        Boolean ischeat: Whetherone or more of the replays involved is cheated.
        ResultType type: What type of cheat test we are representing the results for.
    """

    def __init__(self, ischeat: bool, type_: ResultType):
        """
        Initializes a Result instance.

        Boolean ischeat: Whether one or more of the replays involved is cheated.
        ResultType type: What type of cheat test we are representing the results for.
        """
        self.ischeat = ischeat
        self.type = type_

class InvestigationResult(Result):
    """
    The result of a test for cheats on a single replay.

    Attributes:
        Replay replay: The replay investigated.
        Boolean ischeat: Whether the replay is cheated.
    """

    def __init__(self, replay: Replay, ischeat: bool, type_: ResultType):
        super().__init__(ischeat, type_)
        self.replay = replay

class ComparisonResult(Result):
    """
    The result of a test for cheats by comparing two replays.

    Attributes:
        Replay replay1: One of the replays involved.
        Replay replay2: The other replay involved.
        Boolean ischeat: Whether one of the replays is cheated.
    """

    def __init__(self, replay1: Replay, replay2: Replay, ischeat: bool, type_: ResultType):
        super().__init__(ischeat, type_)
        self.replay1 = replay1
        self.replay2 = replay2

class ReplayStealingResult(ComparisonResult):
    """
    The result of a test for replay stealing between two replays.

    This Result contains the two Replay objects that were compared, and the similarity
    between them. Attributes about the two replays (usernames, mods, map id, etc)
    can be accessed through the replay1 and replay2 objects, as well as the later_replay
    and earlier_replay objects, which are references to one of either replay1 or replay2.

    Attributes:
        Replay replay1: One of the replays involved.
        Replay replay2: The other replay involved.
        Replay earlier_replay: The earlier of the two replays (when the score was made). This is a
                reference to either replay1 or replay2.
        Replay later_replay: The later of the two replays (when the score was made). This is a
                reference to either replay1 or replay2.
        Integer similarity: How similar the two replays are (the lower, the more similar).
        Boolean ischeat: Whether one of the replays is cheated.
    """

    def __init__(self, replay1: Replay, replay2: Replay, similarity: int, ischeat: bool):
        super().__init__(replay1, replay2, ischeat, ResultType.STEAL)

        self.similarity = similarity
        if self.replay1.timestamp < self.replay2.timestamp:
            self.earlier_replay: Replay = self.replay1
            self.later_replay: Replay = self.replay2
        else:
            self.earlier_replay: Replay = self.replay2
            self.later_replay: Replay = self.replay1

class RelaxResult(InvestigationResult):
    """
    The result of a test for relax cheats.

    Attributes:
        Replay replay: The replay investigated.
        Integer ur: The unstable rate of the replay.
        Boolean ischeat: Whether the replay is cheated.
    """

    def __init__(self, replay: Replay, ur: int, ischeat: bool):
        super().__init__(replay, ischeat, ResultType.RELAX)
        self.ur = ur
