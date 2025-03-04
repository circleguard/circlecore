import logging

from ossapi.ossapi import APIException, InvalidKeyException, ReplayUnavailableException

from circleguard.circleguard import Circleguard, KeylessCircleguard, set_options
from circleguard.game_version import GameVersion, NoGameVersion
from circleguard.hitobjects import Circle, Hitobject, Slider, Spinner
from circleguard.investigations import Snap
from circleguard.judgment import Hit, Judgment, JudgmentType, Miss
from circleguard.loadables import (
    CachedReplay,
    Loadable,
    LoadableContainer,
    Map,
    MapUser,
    Replay,
    ReplayCache,
    ReplayContainer,
    ReplayDir,
    ReplayID,
    ReplayMap,
    ReplayOssapi,
    ReplayPath,
    ReplayString,
    User,
)
from circleguard.loader import Loader, NoInfoAvailableException
from circleguard.mod import Mod
from circleguard.span import Span
from circleguard.utils import (
    TRACE,
    ColoredFormatter,
    Key,
    RatelimitWeight,
    convert_statistic,
    fuzzy_mods,
    hitradius,
    hitwindow,
    hitwindows,
    order,
    replay_pairs,
)
from circleguard.version import __version__

logging.addLevelName(TRACE, "TRACE")
formatter = ColoredFormatter(
    "[%(threadName)s][%(name)s][%(levelname)s]  %(message)s  (%(filename)s:%(lineno)s)"
)
handler_stream = logging.StreamHandler()
handler_stream.setFormatter(formatter)
logging.getLogger("circleguard").addHandler(handler_stream)

# don't expose ColoredFormatter to consumers
del ColoredFormatter

__all__ = [
    # core
    "Circleguard",
    "KeylessCircleguard",
    "set_options",
    # loadables
    "ReplayContainer",
    "Map",
    "User",
    "MapUser",
    "ReplayCache",
    "Replay",
    "ReplayMap",
    "ReplayPath",
    "CachedReplay",
    "Loadable",
    "ReplayID",
    "ReplayDir",
    "ReplayString",
    "LoadableContainer",
    "ReplayOssapi",
    # enums
    "Key",
    "RatelimitWeight",
    # mod
    "Mod",
    # utils
    "convert_statistic",
    "order",
    "Key",
    "RatelimitWeight",
    "TRACE",
    "replay_pairs",
    "fuzzy_mods",
    "hitwindow",
    "hitwindows",
    "hitradius",
    # loader
    "Loader",
    # exceptions
    "APIException",
    "NoInfoAvailableException",
    "InvalidKeyException",
    "ReplayUnavailableException",
    # version
    "__version__",
    # investigation-related classes
    "Snap",
    "Judgment",
    "Hit",
    "Miss",
    "JudgmentType",
    # span
    "Span",
    # GameVersion
    "GameVersion",
    "NoGameVersion",
    # hitobjects
    "Hitobject",
    "Circle",
    "Slider",
    "Spinner",
]
