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

int_to_mod = {
    0           : ["NoMod",         "NM"],
    1           : ["NoFail",        "NF"],
    2           : ["Easy",          "EZ"],
    4           : ["NoVideo",       "NV"],
    8           : ["Hidden",        "HD"],
    16          : ["HardRock",      "HR"],
    32          : ["SuddenDeath",   "SD"],
    64          : ["DoubleTime",    "DT"],
    128         : ["Relax",         "RL"],
    256         : ["HalfTime",      "HT"],
    512         : ["Nightcore",     "NC"],
    1024        : ["Flashlight",    "FL"],
    2048        : ["Autoplay",      "CN"],
    4096        : ["SpunOut",       "SO"],
    8192        : ["Autopilot",     "AP"],
    16384       : ["Perfect",       "PF"],
    32768       : ["Key4",          "K4"],
    65536       : ["Key5",          "K5"],
    131072      : ["Key6",          "K6"],
    262144      : ["Key7",          "K7"],
    524288      : ["Key8",          "K8"],
    1015808     : ["keyMod",        "KM"],
    1048576     : ["FadeIn",        "FI"],
    2097152     : ["Random",        "RD"],
    4194304     : ["LastMod",       "LM"],
    8388608     : ["TargetPractice","TP"],
    16777216    : ["Key9",          "K9"],
    33554432    : ["Coop",          "CO"],
    67108864    : ["Key1",          "K1"],
    134217728   : ["Key3",          "K3"],
    268435456   : ["Key2",          "K2"]
}
        
class Mod():
    def __init__(self, input_enum):
        if isinstance(input_enum, str):
            self.value = [k for k, v in int_to_mod.items() if input_enum in v][0]
        else:
            self.value = input_enum
        current_array = int_to_mod[self.value]
        self.name = current_array[0]
        self.short_name = current_array[1]

    def __eq__(self, other):
        """Override the default Equals behavior"""
        return self.value == other.value

    def __ne__(self, other):
        """Override the default Unequal behavior"""
        return self.value != other.value
    
    def __hash__(self):
        return self.value

class Detect(Flag):
                   # (in binary)
    STEAL = 1 << 0 # 0001
    RELAX = 1 << 1 # 0010
    REMOD = 1 << 2 # 0100

    ALL = STEAL | RELAX | REMOD
    NONE = 0

class RatelimitWeight(Enum):
    """
    How much it 'costs' to load a replay from the api. If the load method of a replay makes no api calls,
    the corresponding value is RatelimitWeight.NONE. If it makes only light api calls (anything but get_replay),
    the corresponding value is RatelimitWeight.LIGHT. If it makes any heavy api calls (get_replay), the
    corresponding value is RatelimitWeight.HEAVY.

    This value currently has no effect on the program and is reserved for possible future functionality.
    """

    NONE  = "none"
    LIGHT = "light"
    HEAVY = "heavy"

class ResultType(Enum):
    """
    What type of cheat test we are representing the results for.
    """

    STEAL = "replay stealing"
    REMOD = "remodding"
    RELAX = "relax"
    AIM_CORRECTION = "aim correction"
    TIMEWARP = "timewarp"

class Keys(IntFlag):
    M1 = 1
    M2 = 2
    K1 = 4
    K2 = 8
    SMOKE = 16
