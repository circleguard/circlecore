import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from replay import Replay


class Draw():

    @staticmethod
    def draw_replays(user_replay, check_replay):

        data1 = user_replay.as_list_with_timestamps()
        data2 = check_replay.as_list_with_timestamps()

        # implement naming data in interpolation
        # if you want a guarantee about the order of the returned data
        (data1, data2) = Replay.interpolate(data1, data2)

        # replace with constants for screen sizes
        data1 = [(512 - d[1], 384 - d[2]) for d in data1]
        data2 = [(512 - d[1], 384 - d[2]) for d in data2]

        data1 = np.transpose(data1)
        data2 = np.transpose(data2)

        plt.ion()
        plot1 = plt.plot(data1[0], data1[1], "red")[0]
        plot2 = plt.plot(data2[0], data2[1], "blue")[0]

        for i in range(len(data1[0])):
            plot1.set_xdata(data1[0][:i])
            plot1.set_ydata(data1[1][:i])

            plot2.set_xdata(data2[0][0:i])
            plot2.set_ydata(data2[1][0:i])

            plt.draw()
            plt.pause(0.0001)
