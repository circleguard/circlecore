import logging

from circleguard.circleguard import Circleguard, set_options
from circleguard.replay import Check, Replay, ReplayMap, ReplayPath
from circleguard.enums import Detect
from circleguard.utils import TRACE, ColoredFormatter

__version__ = "2.0.1"

logging.addLevelName(TRACE, "TRACE")
formatter = ColoredFormatter("[%(threadName)s][%(name)s][%(levelname)s]  %(message)s  (%(filename)s:%(lineno)s)")
handler_stream = logging.StreamHandler()
handler_stream.setFormatter(formatter)
logging.getLogger("circleguard").addHandler(handler_stream)
