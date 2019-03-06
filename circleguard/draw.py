import numpy as np
import matplotlib
if(matplotlib.get_backend() == "MacOSX"):
    matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import itertools as itr
from matplotlib.animation import FuncAnimation
from replay import Replay
from enums import Mod

class Draw():
    """
    Displays a visualization of two replays.

    Attributes:
        Replay replay1: The first replay to draw.
        Replay replay2: The second replay to draw.
    """

    def __init__(self, replay1, replay2):
        """
        Initializes a Draw instance.

        Args:
            Replay replay1: The first replay to draw.
            Replay replay2: The second replay to draw.
        """

        self.replay1 = replay1
        self.replay2 = replay2

    def run(self):
        """
        Displays a visualization of two replays on top of each other.

        Args:
            Replay replay1: The first Replay to draw.
            Replay replay2: The second Replay to draw.
        """

        data1 = self.replay1.as_list_with_timestamps()
        data2 = self.replay2.as_list_with_timestamps()

        # synchronize and interpolate
        (data1, data2) = Replay.interpolate(data1, data2, unflip=True)

        # skip breaks (risk pain if you don't sync first)
        data1 = Replay.skip_breaks(data1)
        data2 = Replay.skip_breaks(data2)

        # implement naming data in interpolation
        # if you want a guarantee about the order of the returned data
        fps = 60
        dt = 0

        data1 = Replay.resample(data1, fps)
        data2 = Replay.resample(data2, fps)

        flip1 = Mod.HardRock.value in [mod.value for mod in self.replay1.enabled_mods]
        flip2 = Mod.HardRock.value in [mod.value for mod in self.replay2.enabled_mods]
        # replace with constants for screen sizes
        if(flip1 ^ flip2): # xor, if one has hr but not the other
            data1 = [(512 - d[1], d[2]) for d in data1]
        else:
            data1 = [(512 - d[1], 384 - d[2]) for d in data1]
        data2 = [(512 - d[1], 384 - d[2]) for d in data2]

        data1 = np.transpose(data1)
        data2 = np.transpose(data2)

        # create plot for each replay and add legend with player names
        fig, ax = plt.subplots()

        plot1 = plt.plot('x', 'y', "red", animated=True, label='\u200B' + self.replay1.player_name)[0]
        plot2 = plt.plot('', '', "blue", animated=True, label='\u200B' + self.replay2.player_name)[0]

        fig.legend()

        def init():
            ax.set_xlim(0, 512)
            ax.set_ylim(0, 384)
            return plot1, plot2

        def update(i):
            plot1.set_data(data1[0][i - 100:i], data1[1][i - 100:i])
            plot2.set_data(data2[0][i - 100:i], data2[1][i - 100:i])
            return plot1, plot2
        try:
            animation = FuncAnimation(fig, update, frames=itr.count(100), init_func=init, blit=True, interval=dt)
        except:
            # if you close the window sometimes it's in the middle of updating and prints an annoying string to the console as an error -
            # invalid command name "4584907080_on_timer"... and matplotlib errors are either awful and hidden or I'm blind so here's a blankey
            # try/except
            pass

        plt.show(block=True)

        # keep a reference to this otherwise it will get garbage collected instantly and not play.
        return animation
