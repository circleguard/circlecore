import numpy as np
import matplotlib
if(matplotlib.get_backend() == "MacOSX"):
    matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import itertools as itr
from matplotlib.animation import FuncAnimation
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

        # create plot for each replay and add legend with player names
        fig, ax = plt.subplots()

        plot1 = plt.plot('x', 'y', "red", animated=True, label=self.replay1.player_name)[0]
        plot2 = plt.plot('', '', "blue", animated=True, label=self.replay2.player_name)[0]

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

    @staticmethod
    def color(i, n):
        if n < 2:
            return 'r'
        else:
            return matplotlib.colors.hsv_to_rgb((i / (n - 1), 1, 1))

    @staticmethod
    def fplot(replays, unary=(), binary=()):
        data = [r.as_list_with_timestamps() for r in replays]

        data[1:] = [Replay.interpolate(d, data[0], unflip=True)[0] for d in data[1:]]
        data = [Replay.skip_breaks(d) for d in data]
        data = [(512 - d[1], 384 - d[2]) for d in data]

        # unary and binary should be passed as tuples of (type, func) where type
        # 0 : scalar, dot on curve
        # 1 : vector, vector on curve
        # 2 : replay, new replay
        unary_out = np.zeros((3, 0)).tolist()
        binary_out = np.zeros((3, 0)).tolist()
        for u in unary:
            unary_out[u[0]].append([u[1](d) for d in data])

        for b in binary:
            binary_out[b[0]].append([[b[1](d1, d2) for d2 in data[i:]] for i, d2 in enumerate(data)])

        data = [np.transpose(d) for d in data]

        fig, ax = plt.subplots()

        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_xlim(0, 512)
        ax.set_ylim(0, 384)

        rplots = []
        uplots = np.zeros((3, 0)).tolist()
        uquivers = []
        bplots = np.zeros((3, 0)).tolist()
        bquivers = []
        plots = []

        def init():
            nonlocal rplots, uplots, uquivers bplots, bquivers, plots

            rplots = [plt.plot('', '', Draw.color(i, len(replays)),
                               animated=True, label=r.player_name)[0]
                      for r in replays]

            for u in unary_out[0]:
                scalars = [plt.plot('', '', Draw.color(i, len(u))
                                           , animated=True)[0]
                                  for s in u]
                uplots[0].append(scalars)
                plots.extend(scalars)

            for u in unary_out[1]:
                vectors = [plt.quiver([0], [0], Draw.color(i, len(u))
                                           , animated=True)[0]
                                  for v in u]
                uplots[1].append(vectors)
                plots.extend(vectors)
                uquivers.append([plt.quiverkey(v, 0, 0, 0, '') for v in vectors])

            for u in unary_out[2]:
                new_replays = [plt.plot('', '', Draw.color(i, len(u))
                                           , animated=True)[0]
                                  for r in u]
                uplots[2].append(new_replays)
                plots.extend(new_replays)

            for b in binary_out[0]:
                scalars = [[plt.plot('', '', Draw.color(i, len(u))
                                           , animated=True)[0] for s in b1]
                                  for b1 in b]
                bplots[0].append(scalars)

                for s in scalars:
                    plots.extend(s)
                
            for b in binary_out[1]:
                vectors = [[plt.quiver([0], [0], Draw.color(i, len(u))
                                           , animated=True)[0] for v in b1]
                                  for b1 in b]
                bplots[1].append(vectors)
                bquivers.append([[plt.quiverkey(v, 0, 0, 0, '') for v in v1]
                                  for v1 in vectors]])

                for v in vectors:
                    plots.extend(v)
                
            for b in binary_out[2]:
                new_replays = [[plt.plot('', '', Draw.color(i, len(u))
                                           , animated=True)[0] for r in b1]
                                  for b1 in b]
                bplots[2].append(new_replays)

                for r in new_replays:
                    plots.extend(r)

            fig.legend()

            return plots

        def update(i):
            for plot, replay in zip(rplots, data):
                plot.set_data(replay[0][i - 100:i], replay[1][i - 100:i])
                
            
            for scalars, plots in zip(unary_out[0], uplots[0]):
                for plot, scalar, replay in zip(plots, scalars, data):
                    plot.set_data(replay[0][i], replay[1][i])
                    plot.set_markersize(scalar)

            for vectors, quivers, keys in zip(unary_out[1], uplots[1], uquivers):
                for j, (quiver, vector, replay) in enumerate(zip(quivers, vectors, data)):
                    keys[j].remove()

                    l, t = np.linalg.norm(vector[i]), np.angle(vector[i])

                    keys[j] = plt.quiverkey(quiver, replay[0][i], replay[1][i], l, '', color=Draw.color(k, len(quivers))) 
            
