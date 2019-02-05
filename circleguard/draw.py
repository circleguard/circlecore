import numpy as np
import matplotlib
if(matplotlib.get_backend() == "MacOSX"):
    matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import itertools as itr
import matplotlib.animation
from replay import Replay

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

        # replace with constants for screen sizes
        data1 = [(512 - d[1], 384 - d[2]) for d in data1]
        data2 = [(512 - d[1], 384 - d[2]) for d in data2]

        data1 = np.transpose(data1)
        data2 = np.transpose(data2)

        total = len(data1[0])  # stationary cause otherwise it would be a pain

        def setup():
            global plot1, plot2, fig, ax, animation

            # create plot for each replay and add legend with player names
            fig, ax = plt.subplots()

            plot1 = plt.plot('x', 'y', "red", animated=True, label=self.replay1.player_name)[0]
            plot2 = plt.plot('', '', "blue", animated=True, label=self.replay2.player_name)[0]

            fig.legend()
            animation = animation.FuncAnimation(fig, update, frames=len(data1[0]), init_func=init, blit=True, interval=1)
            init()
            return

        def init():
            ax.set_xlim(0, 512)
            ax.set_ylim(0, 384)
            return plot1, plot2

        def update(i):
            plot1.set_data(data1[0][i - 100:i], data1[1][i - 100:i])
            plot2.set_data(data2[0][i - 100:i], data2[1][i - 100:i])
            if i != 0 and i % int((total/10)) == 0:
                print(f"Saved {round(100 * float(i)/float(total))}% of the video")
            return plot1, plot2

        setup()
        
        plt.show(block=True)
        plt.close('all')  # Maybe unnecessary
        if input("Do you want to save the video? WARNING, this may take a while ")[0] == "y":
            print("started saving video")
            setup()

            writer = mk_animation.writers['ffmpeg']
            writer = Writer(fps=60, metadata=dict(artist='Me'), bitrate=1800, )

            file_name = f'{self.replay1.player_name[0]} vs {self.replay1.player_name[0]}.mp4'
            animation.save(file_name, writer=writer)

            print(f"Saved Video as {file_name}")


        # keep a reference to this otherwise it will get garbage collected instantly and not play.
        return animation
