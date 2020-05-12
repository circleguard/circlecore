from enum import Enum, Flag, IntFlag

from circleguard.exceptions import (UnknownAPIException, RatelimitException,
                InvalidKeyException, ReplayUnavailableException, InvalidJSONException)

# strings taken from osu api error responses
# [api response, exception class type, details to pass to an exception]
class Error(Enum):
    NO_REPLAY         = ["Replay not available.", ReplayUnavailableException, "Could not find any replay data. Skipping"]
    RATELIMITED       = ["Requesting too fast! Slow your operation, cap'n!", RatelimitException, "We were ratelimited. Waiting it out"]
    RETRIEVAL_FAILED  = ["Replay retrieval failed.", ReplayUnavailableException, "Replay retrieval failed. Skipping"]
    INVALID_KEY       = ["Please provide a valid API key.", InvalidKeyException, "Please provide a valid api key"]
    INVALID_JSON      = ["The api broke.", InvalidJSONException, "The api returned an invalid json response, retrying"]
    UNKNOWN           = ["Unknown error.", UnknownAPIException, "Unknown error when requesting a replay. Please report this "
                                                                "to the developers at https://github.com/circleguard/circlecore"]


class RatelimitWeight(Enum):
    """
    How much it 'costs' to load a replay from the api.

    :data:`~.RatelimitWeight.NONE` if the load method of a replay makes no api
    calls.

    :data:`~.RatelimitWeight.LIGHT` if the load method of a replay makes only
    light api calls (anything but ``get_replay``).

    :data:`~.RatelimitWeight.HEAVY` if the load method of a replay makes any
    heavy api calls (``get_replay``).

    Notes
    -----
    This value currently has no effect on the program and is reserved for
    future functionality.
    """

    NONE  = "None"
    LIGHT = "Light"
    HEAVY = "Heavy"


class Detect(IntFlag):
    """
    A cheat, or set of cheats, to investigate for.

    Notes
    -----
    Also defines thresholds we feel are reasonable to determine a replay as
    cheated. These values are more conservative - that is, we try to not give
    false positives. You should decide where you fall on the scale
    of "few false positives, many false negatives" to "many false positives,
    few false negatives" for yourself, if necessary.
    """
    STEAL      = 1 << 0
    RELAX      = 1 << 1
    CORRECTION = 1 << 2
    ALL        = STEAL + RELAX + CORRECTION

    SIM_LIMIT = 17
    # unconverted ur threshold
    UR_LIMIT = 50
    # no aim correction threshold - any snap is suspicious


class ResultType(Enum):
    """
    What type of cheat test to represent the results for.
    """

    STEAL = "Replay Stealing"
    REMOD = "Remodding"
    RELAX = "Relax"
    CORRECTION = "Aim Correction"
    TIMEWARP = "Timewarp"


class Key(IntFlag):
    M1    = 1 << 0
    M2    = 1 << 1
    K1    = 1 << 2
    K2    = 1 << 3
    SMOKE = 1 << 4
