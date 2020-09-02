import logging

from circleguard.circleguard import Circleguard, KeylessCircleguard, set_options
from circleguard.loadable import (Check, Replay, ReplayMap, ReplayPath, Map, User,
        MapUser, ReplayDir, ReplayContainer, LoadableContainer, Loadable, ReplayCache,
        CachedReplay, ReplayID, ReplayString)
from circleguard.enums import Key, RatelimitWeight, Detect, ResultType
from circleguard.mod import Mod
from circleguard.utils import TRACE, ColoredFormatter
from circleguard.loader import Loader
from circleguard.replay_info import ReplayInfo
from circleguard.exceptions import (CircleguardException, InvalidArgumentsException, APIException,
        NoInfoAvailableException, UnknownAPIException, InternalAPIException, InvalidKeyException, RatelimitException,
        InvalidJSONException, ReplayUnavailableException)
from circleguard.version import __version__
from circleguard.result import (Result, InvestigationResult, ComparisonResult,
        StealResult, StealResultSim, StealResultCorr, RelaxResult,
        CorrectionResult, TimewarpResult)
from circleguard.investigator import Snap, Hit
from circleguard.span import Span
from circleguard.utils import convert_statistic

logging.addLevelName(TRACE, "TRACE")
formatter = ColoredFormatter("[%(threadName)s][%(name)s][%(levelname)s]  %(message)s  (%(filename)s:%(lineno)s)")
handler_stream = logging.StreamHandler()
handler_stream.setFormatter(formatter)
logging.getLogger("circleguard").addHandler(handler_stream)

__all__ = [
# core
"Circleguard", "KeylessCircleguard", "set_options",
# loadables
"Check", "ReplayContainer", "LoadableContainer", "Map", "User", "MapUser",
"ReplayCache", "Replay", "ReplayMap", "ReplayPath", "CachedReplay", "Loadable",
"ReplayID", "ReplayDir", "ReplayString",
# enums
"Key", "RatelimitWeight", "Detect", "ResultType",
# mod
"Mod",
# utils
"TRACE",
# loader
"Loader",
# replay info
"ReplayInfo",
# exceptions
"CircleguardException", "InvalidArgumentsException", "APIException",
"NoInfoAvailableException", "UnknownAPIException", "InternalAPIException",
"InvalidKeyException", "RatelimitException", "InvalidJSONException",
"ReplayUnavailableException",
# version
"__version__",
# results
"Result", "InvestigationResult", "ComparisonResult", "StealResult",
"StealResultSim", "StealResultCorr", "RelaxResult", "CorrectionResult",
"TimewarpResult",
# results-related classes
"Snap", "Hit",
# span
"Span",
# utils
"convert_statistic"
]
