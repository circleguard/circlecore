from circleguard.loadable import Replay
from circleguard.enums import ResultType
from circleguard.utils import convert_statistic

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
    def __init__(self, type_: ResultType):
        self.type = type_

class InvestigationResult(Result):
    """
    The result of a test for cheats on a single replay.

    Parameters
    ----------
    replay: :class:`~circleguard.loadable.Replay`
        The replay investigated.
    """

    def __init__(self, replay: Replay, type_: ResultType):
        super().__init__(type_)
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
    """

    def __init__(self, replay1: Replay, replay2: Replay, type_: ResultType):
        super().__init__(type_)
        self.replay1 = replay1
        self.replay2 = replay2

class StealResult(ComparisonResult):
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
        reference to either replay1 or replay2, or ``None`` if one of the
        replays did not provide a timestamp.
    later_replay: :class:`~circleguard.loadable.Replay`
        The later of the two replays (when the score was made). This is a
        reference to either replay1 or replay2, or ``None`` if one of the
        replays did not provide a timestamp.
    similarity: int
        The similarity of the two replays (the lower, the more similar).
        Similarity is, roughly speaking, a measure of the average pixel
        distance between the two replays.
    correlation: float
        The median correlation of the two replays (the closer to 1, the more correlated).
        A value of 1.0 would be perfectly correlated, and a result of 0 would be uncorrelated.
    """

    def __init__(self, replay1: Replay, replay2: Replay):
        super().__init__(replay1, replay2, ResultType.STEAL)

        # can't compare ``None`` timestamps
        if not self.replay1.timestamp or not self.replay2.timestamp:
            return

        if self.replay1.timestamp < self.replay2.timestamp:
            self.earlier_replay: Replay = self.replay1
            self.later_replay: Replay = self.replay2
        else:
            self.earlier_replay: Replay = self.replay2
            self.later_replay: Replay = self.replay1


class StealResultSim(StealResult):
    """
    The result of a test for replay stealing between two replays, using
    the similarity algorithm.

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
        The similarity of the two replays (the lower, the more similar).
        Similarity is, roughly speaking, a measure of the average pixel
        distance between the two replays.
    """
    def __init__(self, replay1: Replay, replay2: Replay, similarity: float):
        super().__init__(replay1, replay2)
        self.similarity: float = similarity


class StealResultCorr(StealResult):
    """
    The result of a test for replay stealing between two replays, using
    the similarity algorithm.

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
        The similarity of the two replays (the lower, the more similar).
        Similarity is, roughly speaking, a measure of the average pixel
        distance between the two replays.
    """
    def __init__(self, replay1: Replay, replay2: Replay, correlation: float):
        super().__init__(replay1, replay2)
        self.correlation: float = correlation


class RelaxResult(InvestigationResult):
    """
    The result of a test for relax cheats.

    Parameters
    ----------
    replay: :class:`~circleguard.loadable.Replay`
        The replay investigated.
    ur: float
        The (unconverted) unstable rate of the replay. More information on UR
        available at https://osu.ppy.sh/help/wiki/Accuracy#accuracy
    """
    def __init__(self, replay: Replay, ur: float):
        super().__init__(replay, ResultType.RELAX)
        self.ur = convert_statistic(ur, replay.mods, to="cv")
        self.ucv_ur = ur


class CorrectionResult(InvestigationResult):
    """
    The result of a test for aim correction cheats.

    Parameters
    ----------
    replay: :class:`~circleguard.loadable.Replay`
        The replay investigated.
    snaps: list[:class:`~circleguard.investigator.Snap`]
        A list of suspicious hits in the replay.
    """

    def __init__(self, replay: Replay, snaps: list):
        super().__init__(replay, ResultType.CORRECTION)
        self.snaps = snaps


class TimewarpResult(InvestigationResult):
    """
    The result of a test for timewarp cheats.

    Parameters
    ----------
    replay: :class:`~circleguard.loadable.Replay`
        The replay investigated.
    frametime: float
        The average (median) time between frames of the replay.
    """

    def __init__(self, replay: Replay, frametime: float):
        super().__init__(replay, ResultType.TIMEWARP)
        self.frametime = convert_statistic(frametime, replay.mods, to="cv")
        self.ucv_frametime = frametime
