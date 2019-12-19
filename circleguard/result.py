from circleguard.loadable import Replay
from circleguard.enums import ResultType

# Hierarchy
#                                 Result
#          InvestigationResult             ComparisonResult
#      RelaxResult, CorrectionResult       ReplayStealingResult
#
#
class Result():
    """
    The result of a test for cheats, either on a single replay or a
    collection of replays.

    Parameters
    ----------
    ischeat: bool
        Whether one or more of the replays involved is cheated or not.
    type: :class:`~circleguard.enums.ResultType`
        What type of cheat test we are representing the results for.
    """
    def __init__(self, ischeat: bool, type_: ResultType):
        self.ischeat = ischeat
        self.type = type_

class InvestigationResult(Result):
    """
    The result of a test for cheats on a single replay.

    Parameters
    ----------
    replay: :class:`~circleguard.loadable.Replay`
        The replay investigated.
    ischeat: bool
        Whether the replay is cheated or not.
    """

    def __init__(self, replay: Replay, ischeat: bool, type_: ResultType):
        super().__init__(ischeat, type_)
        self.replay = replay

class ComparisonResult(Result):
    """
    The result of a test for cheats by comparing two replays.

    Parameters
    ----------
    replay1: :class:`~circleguard.loadable.Replay`
        One of the replays involved.
    replay2: :class:`~circleguard.loadable.Replay`
        The other replay involved.
    ischeat: bool
        Whether one of the replays is cheated or not.
    """

    def __init__(self, replay1: Replay, replay2: Replay, ischeat: bool, type_: ResultType):
        super().__init__(ischeat, type_)
        self.replay1 = replay1
        self.replay2 = replay2

class ReplayStealingResult(ComparisonResult):
    """
    The result of a test for replay stealing between two replays.

    Parameters
    ----------
    replay1: :class:`~circleguard.loadable.Replay`
        One of the replays involved.
    replay2: :class:`~circleguard.loadable.Replay`
        The other replay involved.
    earlier_replay: :class:`~circleguard.loadable.Replay`
        The earlier of the two replays (when the score was made). This is a
        reference to either replay1 or replay2.
    later_replay: :class:`~circleguard.loadable.Replay`
        The later of the two replays (when the score was made). This is a
        reference to either replay1 or replay2.
    similarity: int
        How similar the two replays are (the lower, the more similar).
        Similarity is, roughly speaking, a measure of the average pixel
        distance between the two replays.
    ischeat: bool
        Whether one of the replays is cheated or not.
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

    Parameters
    ----------
    replay: :class:`~circleguard.loadable.Replay`
        The replay investigated.
    ur: int
        The unstable rate of the replay. More information on UR available at
        https://osu.ppy.sh/help/wiki/Accuracy#accuracy
    ischeat: bool
        Whether the replay is cheated or not.
    """
    def __init__(self, replay: Replay, ur: int, ischeat: bool):
        super().__init__(replay, ischeat, ResultType.RELAX)
        self.ur = ur

class CorrectionResult(InvestigationResult):
    """
    The result of a test for aim correction cheats.

    Parameters
    ----------
    replay: :class:`~circleguard.loadable.Replay`
        The replay investigated.
    snaps: list[:class:`~circleguard.investigator.Snap`]
        A list of suspicious hits in the replay.
    ischeat: bool
        Whether the replay is cheated or not.
    """

    def __init__(self, replay, snaps, ischeat):
        super().__init__(replay, ischeat, ResultType.CORRECTION)
        self.snaps = snaps


class MacroResult(InvestigationResult):
    def __init__(self, replay, presses, ischeat):
        super().__init__(replay, ischeat, ResultType.MACRO)
        self.presses = presses
