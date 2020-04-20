class Detect():
    """
    A cheat, or set of cheats, to run tests to detect.

    Parameters
    ----------
    value: int
        One (or a bitwise combination) of :data:`~.Detect.STEAL`,
        :data:`~.Detect.RELAX`, :data:`~.Detect.CORRECTION`,
        :data:`~.Detect.ALL`. What cheats to detect.
    """
    STEAL = 1 << 0
    RELAX = 1 << 1
    CORRECTION = 1 << 2
    ALL = STEAL + RELAX + CORRECTION

    def __init__(self, value):
        self.value = value

        # so we can reference them in :func:`~.__add__`
        self.max_sim = None
        self.max_ur = None
        self.max_angle = None
        self.min_distance = None

    def __contains__(self, other):
        return bool(self.value & other)

    def __add__(self, other):
        ret = Detect(self.value | other.value)
        d = self if Detect.STEAL in self else other if Detect.STEAL in other else None
        if d:
            ret.max_sim = d.max_sim
        d = self if Detect.RELAX in self else other if Detect.RELAX in other else None
        if d:
            ret.max_ur = d.max_ur
        d = self if Detect.CORRECTION in self else other if Detect.CORRECTION in other else None
        if d:
            ret.max_angle = d.max_angle
            ret.min_distance = d.min_distance
        return ret

class StealDetect(Detect):
    """
    Defines a detection of replay stealing.

    Look at the average distance between the cursors of two replays.

    Parameters
    ----------
    max_sim: float
        If the average distance in pixels of two replays is smaller than
        this value, they are labeled cheated (aka the replays are stolen).
    """
    DEFAULT_SIM = 18
    def __init__(self, max_sim=DEFAULT_SIM):
        super().__init__(Detect.STEAL)
        self.max_sim = max_sim

class RelaxDetect(Detect):
    """
    Defines a detection of relax.

    Look at the ur of a replay.

    Parameters
    ----------
    max_ur: float
        If the ur of a replay is less than this value, it is labeled cheated
        (relaxed).
    """
    DEFAULT_UR = 50
    def __init__(self, max_ur=DEFAULT_UR):
        super().__init__(Detect.RELAX)
        self.max_ur = max_ur

class CorrectionDetect(Detect):
    """
    Defines a detection of aim correction.

    Look at each set of three points (a,b,c) in a replay and calculate the
    angle between them. Look at points where this angle is extremely acute
    and neither ``|ab|`` or ``|bc|`` are small.

    Parameters
    ----------
    max_angle: float
        Consider only (a,b,c) where ``∠abc < max_angle``.
    min_distance: float
        Consider only (a,b,c) where ``|ab| > min_distance`` and
        ``|ab| > min_distance``.

    Notes
    -----
    A replay is considered cheated (aim corrected) by this detect if there
    is a single datapoint that satsfies both ``max_angle`` and
    ``min_distance``.
    """
    DEFAULT_ANGLE = 10
    DEFAULT_DISTANCE = 8
    def __init__(self, max_angle=DEFAULT_ANGLE, min_distance=DEFAULT_DISTANCE):
        super().__init__(Detect.CORRECTION)
        self.max_angle = max_angle
        self.min_distance = min_distance
