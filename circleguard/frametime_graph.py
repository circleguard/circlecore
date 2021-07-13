import numpy as np
try:
    from matplotlib import pyplot
except ImportError:
    raise ImportError("matplotlib must be installed to create frametime graphs")

from circleguard.mod import Mod
from circleguard.circleguard import KeylessCircleguard

# classes that import optional modules have to be in their own file, or else
# they get imported and evaluated (and potentially error) when circlecore is
# imported. We can fix this by wrapping the entire definition in a
# try/catch/pass, but then we can't give a nice error message when people try to
# use this class without installing matplotlib. Another file isn't the end of
# the world.

class FrametimeGraph:
    # for any frametimes larger than this, chuck them into a single bin.
    # matplotlib can't really handle that many bins otherwise
    MAX_FRAMETIME = 50

    def __init__(self, replay, cv, figure, show_expected_frametime):
        self.cv = cv
        # figsize is in inches for whatever reason lol
        self.figure = figure or pyplot.figure(figsize=(5, 5))
        self.show_expected_frametime = show_expected_frametime
        conversion_factor_raw = self._conversion_factor(replay)
        self.conversion_factor = conversion_factor_raw if self.cv else 1
        self.expected_frametime = 16 + 2 / 3
        if not self.cv:
            self.expected_frametime /= conversion_factor_raw

        # replay is guaranteed to be loaded when we get it
        cg = KeylessCircleguard()
        # we convert the frametimes manually if necessary later on instead of
        # relying on our conversion in this method, since there are a few
        # oddities about the frametime graph which make it easier this way.
        frametimes = cg.frametimes(replay, cv=False)

        self.figure.suptitle(f"Frametimes for {replay.username} "
            f"+{replay.mods.short_name()} on b/{replay.map_id}")

        self.max_frametime = max(frametimes)
        if self.max_frametime > self.MAX_FRAMETIME:
            self.plot_with_break(frametimes)
        else:
            self.plot_normal(frametimes)

    def plot_normal(self, frametimes):
        frametimes = self.conversion_factor * frametimes
        ax = self.figure.subplots()

        bins = np.arange(0, (self.conversion_factor * self.max_frametime) + 1,
            self.conversion_factor)
        ax.hist(frametimes, bins)
        ax.set_xlabel("Frametime")
        ax.set_ylabel("Count")

        if self.show_expected_frametime:
            ax.axvline(x=self.expected_frametime, color="red")

    # adapted from
    # https://matplotlib.org/examples/pylab_examples/broken_axis.html
    def plot_with_break(self, frametimes):
        # gridspec_kw to make outlier plot smaller than the main one.
        # https://stackoverflow.com/a/35881382
        ax1, ax2 = self.figure.subplots(1, 2, sharey=True,
            gridspec_kw={"width_ratios": [3, 1]})
        ax1.spines["right"].set_visible(False)
        ax2.spines["left"].set_visible(False)
        ax1.set_xlabel("Frametime")
        ax1.set_ylabel("Count")

        ax2.tick_params(left=False)

        low_frametime_truth_arr = frametimes <= self.MAX_FRAMETIME
        low_frametimes = frametimes[low_frametime_truth_arr]
        high_frametimes = frametimes[~low_frametime_truth_arr]

        low_frametimes = self.conversion_factor * low_frametimes
        high_frametimes = self.conversion_factor * high_frametimes

        bins = np.arange(0, (self.conversion_factor * self.MAX_FRAMETIME) + 1,
            self.conversion_factor)
        ax1.hist(low_frametimes, bins)
        # -1 in case high_frametimes has only one frame
        bins = [min(high_frametimes) - 1, self.conversion_factor *
            self.max_frametime]
        ax2.hist(high_frametimes, bins)

        if self.show_expected_frametime:
            ax1.axvline(x=self.expected_frametime, color="red")

    def _conversion_factor(self, replay):
        if Mod.DT in replay.mods:
            return 1 / 1.5
        if Mod.HT in replay.mods:
            return 1 / 0.75
        return 1
