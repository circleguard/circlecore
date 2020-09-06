import logging

from circleguard.circleguard import Circleguard, KeylessCircleguard, set_options
from circleguard.loadables import (Replay, ReplayMap, ReplayPath, Map, User,
        MapUser, ReplayDir, ReplayContainer, Loadable, ReplayCache,
        CachedReplay, ReplayID, ReplayString)
from circleguard.enums import Key, RatelimitWeight
from circleguard.mod import Mod
from circleguard.utils import TRACE, ColoredFormatter
from circleguard.loader import Loader
from circleguard.replay_info import ReplayInfo
from circleguard.exceptions import (CircleguardException, InvalidArgumentsException, APIException,
        NoInfoAvailableException, UnknownAPIException, InternalAPIException, InvalidKeyException, RatelimitException,
        InvalidJSONException, ReplayUnavailableException)
from circleguard.version import __version__
from circleguard.investigator import Snap, Hit
from circleguard.span import Span
from circleguard.utils import convert_statistic, order

logging.addLevelName(TRACE, "TRACE")
formatter = ColoredFormatter("[%(threadName)s][%(name)s][%(levelname)s]  %(message)s  (%(filename)s:%(lineno)s)")
handler_stream = logging.StreamHandler()
handler_stream.setFormatter(formatter)
logging.getLogger("circleguard").addHandler(handler_stream)

__all__ = [
# core
"Circleguard", "KeylessCircleguard", "set_options",
# loadables
"ReplayContainer", "Map", "User", "MapUser",
"ReplayCache", "Replay", "ReplayMap", "ReplayPath", "CachedReplay", "Loadable",
"ReplayID", "ReplayDir", "ReplayString",
# enums
"Key", "RatelimitWeight",
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
# results-related classes
"Snap", "Hit",
# span
"Span",
# utils
"convert_statistic", "order"
]
