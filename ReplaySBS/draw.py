import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from replay import Replay
import timeit


class Draw():

    @staticmethod
    def draw_replays(user_replay, check_replay):

        data1 = user_replay.as_list_with_timestamps()
        data2 = check_replay.as_list_with_timestamps()

        # implement naming data in interpolation
        # if you want a guarantee about the order of the returned data
        fps = 60
        dt = 1 / fps

        data1 = Replay.resample(data1, fps)
        data2 = Replay.resample(data2, fps)

        # replace with constants for screen sizes
        data1 = [(512 - d[1], 384 - d[2]) for d in data1]
        data2 = [(512 - d[1], 384 - d[2]) for d in data2]

        data1 = np.transpose(data1)
        data2 = np.transpose(data2)

        # create plot for each replay and add legend with player names
        plt.ion()
        fig, ax = plt.subplots()
        plot1 = plt.plot(data1[0], data1[1], "red", label = user_replay.player_name )[0]
        plot2 = plt.plot(data2[0], data2[1], "blue", label = check_replay.player_name  )[0]
        legend = ax.legend()

        for i in range(len(data1[0])):
            plot1.set_xdata(data1[0][i - 100:i])
            plot1.set_ydata(data1[1][i - 100:i])

            plot2.set_xdata(data2[0][i - 100:i])
            plot2.set_ydata(data2[1][i - 100:i])

            plt.pause(dt)
