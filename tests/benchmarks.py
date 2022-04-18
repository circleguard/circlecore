# Benchmarks for circleguard. These are not strictly "tests" and will not be run
# by unittest, but it felt appropriate to place them in the tests folder.

import cProfile
from pstats import Stats

from circleguard import Circleguard, ReplayPath
from utils import KEY, RES

cg = Circleguard(KEY)

replay1 = ReplayPath(RES / "legit" / "legit-1.osr")
cg.load(replay1)

def benchmark_ur(with_cache):
    """
    Parameters
    ----------
    with_cache: {"none", "replay", "beatmap", "both"}
        What caches to use when calculating the ur of the replay. If "replay",
        a replay that has already been loaded is used. If "beatmap", the beatmap
        is downloaded on the first call, and is cached thereafter. If "both",
        both of the above caches apply.
    """
    profiler = cProfile.Profile()

    if with_cache == "none":
        num_calls = 10
        def benchmark_func():
            # creating a new cg object is a hacky way to force a new slider
            # cache
            cg = Circleguard(KEY)
            replay = ReplayPath(RES / "legit" / "legit-1.osr")
            cg.ur(replay)
    elif with_cache == "replay":
        num_calls = 10
        def benchmark_func():
            cg = Circleguard(KEY)
            cg.ur(replay1)

    elif with_cache == "beatmap":
        num_calls = 100
        def benchmark_func():
            replay = ReplayPath(RES / "legit" / "legit-1.osr")
            cg.ur(replay)

    elif with_cache == "both":
        num_calls = 100
        def benchmark_func():
            cg.ur(replay1)


    profiler.enable()
    for _ in range(num_calls):
        benchmark_func()

    profiler.disable()

    stats = Stats(profiler)
    print(f"Average time per call with cache \"{with_cache}\": {stats.total_tt / num_calls:3f} ({num_calls} calls)")

if __name__ == "__main__":
    benchmark_ur(with_cache="none")
    benchmark_ur(with_cache="beatmap")
    benchmark_ur(with_cache="replay")
    benchmark_ur(with_cache="both")
