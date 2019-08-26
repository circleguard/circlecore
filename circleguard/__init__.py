import logging

from circleguard.circleguard import Circleguard, set_options
from circleguard.replay import Check, Replay, ReplayMap, ReplayPath, Map, Container
from circleguard.enums import Detect, RatelimitWeight
from circleguard.utils import TRACE, ColoredFormatter
from circleguard.loader import Loader
from circleguard.version import __version__
from circleguard.result import Result, InvestigationResult, ComparisonResult, RelaxResult, ReplayStealingResult, ResultType

logging.addLevelName(TRACE, "TRACE")
formatter = ColoredFormatter("[%(threadName)s][%(name)s][%(levelname)s]  %(message)s  (%(filename)s:%(lineno)s)")
handler_stream = logging.StreamHandler()
handler_stream.setFormatter(formatter)
logging.getLogger("circleguard").addHandler(handler_stream)

__all__ = ["Circleguard", "set_options", "Check", "Replay", "ReplayMap",
           "ReplayPath", "Detect", "TRACE", "Loader",
           "__version__", "RatelimitWeight", "Result", "InvestigationResult",
           "ComparisonResult", "RelaxResult", "ReplayStealingResult", "ResultType",
           "Map", "Container"]
