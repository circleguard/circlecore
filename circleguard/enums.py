from enum import Enum, Flag

from circleguard.exceptions import UnknownAPIException, RatelimitException, InvalidKeyException, ReplayUnavailableException
# strings taken from osu api error responses
# [api response, exception class type, details to pass to an exception]
class Error(Enum):
    NO_REPLAY         = ["Replay not available.", ReplayUnavailableException, "Could not find any replay data. Skipping"]
    RATELIMITED       = ["Requesting too fast! Slow your operation, cap'n!", RatelimitException, "We were ratelimited. Waiting it out"]
    RETRIEVAL_FAILED  = ["Replay retrieval failed.", ReplayUnavailableException, "Replay retrieval failed. Skipping"]
    INVALID_KEY       = ["Please provide a valid API key.", InvalidKeyException, "Please provide a valid api key"]
    UNKNOWN           = ["Unknown error.", UnknownAPIException, "Unknown error when requesting a replay. Please report this "
                                                                "to the developers at https://github.com/circleguard/circlecore"]

class Mod(Enum):
    NoMod          = NM = 0
    NoFail         = NF = 1
    Easy           = EZ = 2
    NoVideo        = NV = 4
    Hidden         = HD = 8
    HardRock       = HR = 16
    SuddenDeath    = SD = 32
    DoubleTime     = DT = 64
    Relax          = RL = 128
    HalfTime       = HT = 256
    Nightcore      = NC = 512
    Flashlight     = FL = 1024
    Autoplay       = CN = 2048
    SpunOut        = SO = 4096
    Autopilot      = AP = 8192
    Perfect        = PF = 16384
    Key4           = K4 = 32768
    Key5           = K5 = 65536
    Key6           = K6 = 131072
    Key7           = K7 = 262144
    Key8           = K8 = 524288
    keyMod         = KM = 1015808
    FadeIn         = FI = 1048576
    Random         = RD = 2097152
    LastMod        = LM = 4194304
    TargetPractice = TP = 8388608
    Key9           = K9 = 16777216
    Coop           = CO = 33554432
    Key1           = K1 = 67108864
    Key3           = K3 = 134217728
    Key2           = K2 = 268435456

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

    This value is used internally to determine how long the loader class will have to spend loading replays -
    currently LIGHT and NONE are treated the same, and only HEAVY values are counted towards replays to load.
    See loader#new_session and the Replay documentation for more details.
    """

    NONE  = "none"
    LIGHT = "light"
    HEAVY = "heavy"
