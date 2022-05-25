import cProfile
from pstats import Stats

from circleguard import Circleguard, ReplayPath
from utils import KEY, RES

# TODO not sure how useful this benchmark is tbh, rework or remove

def benchmark_hits_ur(statistic):
    """
    Parameters
    ----------
    statistic: {"hits", "ur", "both"}
        What statistics to calculate
    """
    profiler = cProfile.Profile()


    num_calls = 20
    def benchmark_func():
        cg = Circleguard(KEY)
        replay = ReplayPath(RES / "legit" / "legit-1.osr")
        if statistic in ["hits", "both"]:
            cg.hits(replay)
        if statistic in ["both", "ur"]:
            cg.ur(replay)


    profiler.enable()
    for _ in range(num_calls):
        benchmark_func()

    profiler.disable()

    stats = Stats(profiler)
    print(f"Average time per call with statistic \"{statistic}\": {stats.total_tt / num_calls:3f} ({num_calls} calls)")

if __name__ == "__main__":
    benchmark_hits_ur(statistic="hits")
    benchmark_hits_ur(statistic="ur")
    benchmark_hits_ur(statistic="both")
