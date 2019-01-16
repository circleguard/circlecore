import numpy as np
import matplotlib.pyplot as plt
import itertools as itr
from matplotlib.animation import FuncAnimation
from replay import Replay

class Draw():
    @staticmethod
    def draw_replays(user_replay, check_replay):

        data1 = user_replay.as_list_with_timestamps()
        data2 = check_replay.as_list_with_timestamps()

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
        
        plot1 = plt.plot('x', 'y', "red", animated=True, label=user_replay.player_name)[0]
        plot2 = plt.plot('', '', "blue", animated=True, label=check_replay.player_name)[0]
        legend = ax.legend()

        def init():
            ax.set_xlim(0, 512)
            ax.set_ylim(0, 384)
            return plot1, plot2

        def update(i):
            plot1.set_data(data1[0][i - 100:i], data1[1][i - 100:i])
            plot2.set_data(data2[0][i - 100:i], data2[1][i - 100:i])
            return plot1, plot2

        animation = FuncAnimation(fig, update, frames=itr.count(100), init_func=init, blit=True, interval=dt)
        plt.show(block=True)

        # keep a reference to this otherwise it will get garbage collected instantly and not play.
        return animation
