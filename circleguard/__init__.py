import logging

# ``Mod`` is actually defined in ossapi, but we want that fact to be totally
# transparent to consumers. It logically should be defined in circlecore, but
# since ossapi needs to deal with api responses that return mods, and circlecore
# already depends on ossapi (so ossapi can't depend on circlecore), we needed to
# move ``Mod`` to ossapi. But consumers shouldn't need to be aware of this and
# it should seem as if circlecore is the one that defined ``Mod``.
from ossapi import Mod

from circleguard.circleguard import Circleguard, KeylessCircleguard, set_options
from circleguard.loadables import (Replay, ReplayMap, ReplayPath, Map, User,
        MapUser, ReplayDir, ReplayContainer, Loadable, ReplayCache,
        CachedReplay, ReplayID, ReplayString, LoadableContainer)
from circleguard.loader import (Loader, ReplayInfo, APIException,
        NoInfoAvailableException, UnknownAPIException, InternalAPIException,
        InvalidKeyException, RatelimitException, InvalidJSONException,
        ReplayUnavailableException)
from circleguard.version import __version__
from circleguard.investigator import Snap, Hit
from circleguard.span import Span
from circleguard.utils import (convert_statistic, order, Key,
        RatelimitWeight, TRACE, ColoredFormatter, replay_pairs, fuzzy_mods)
from circleguard.game_version import GameVersion, NoGameVersion
from circleguard.hitobjects import Hitobject, Circle, Slider, Spinner

logging.addLevelName(TRACE, "TRACE")
formatter = ColoredFormatter("[%(threadName)s][%(name)s][%(levelname)s]  %(message)s  (%(filename)s:%(lineno)s)")
handler_stream = logging.StreamHandler()
handler_stream.setFormatter(formatter)
logging.getLogger("circleguard").addHandler(handler_stream)

# don't expose ColoredFormatter to consumers
del ColoredFormatter

__all__ = [
# mod (from ossapi)
"Mod",
# core
"Circleguard", "KeylessCircleguard", "set_options",
# loadables
"ReplayContainer", "Map", "User", "MapUser",
"ReplayCache", "Replay", "ReplayMap", "ReplayPath", "CachedReplay", "Loadable",
"ReplayID", "ReplayDir", "ReplayString", "LoadableContainer",
# enums
"Key", "RatelimitWeight",
# utils
"convert_statistic", "order", "Key", "RatelimitWeight", "TRACE", "replay_pairs",
"fuzzy_mods",
# loader
"Loader", "ReplayInfo",
# exceptions
"APIException",
"NoInfoAvailableException", "UnknownAPIException", "InternalAPIException",
"InvalidKeyException", "RatelimitException", "InvalidJSONException",
"ReplayUnavailableException",
# version
"__version__",
# investigation-related classes
"Snap", "Hit",
# span
"Span",
# GameVersion
"GameVersion", "NoGameVersion",
# hitobjects
"Hitobject", "Circle", "Slider", "Spinner"
]
