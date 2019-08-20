from circleguard.enums import Detect

steal_thresh = 18
rx_thresh = 50
num = 50
stddevs = None
cache = False
failfast = False

def include_predicate(replay):
    return True

include = include_predicate
detect = Detect.ALL
