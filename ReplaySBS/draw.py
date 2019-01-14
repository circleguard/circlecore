import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from replay import Replay


class Draw():

    @staticmethod
    def draw_replays(user_replay, check_replay):

        user_coords_x, check_coords_x = [], []
        user_coords_y, check_coords_y = [], []

        for frame in user_replay:
            user_coords_x.append(512-frame.x)
            user_coords_y.append(384-frame.y)

        for frame in check_replay:
            check_coords_x.append(512-frame.x)
            check_coords_y.append(384-frame.y)

        plt.ion()
        user_plot= plt.plot(user_coords_x, user_coords_y, "red")[0]
        checked_plot = plt.plot(check_coords_x, check_coords_y, "blue")[0]

        for i in range(len(user_coords_x)):
            user_plot.set_xdata(user_coords_x[0:i])
            user_plot.set_ydata(user_coords_y[0:i])

            checked_plot.set_xdata(check_coords_x[0:i])
            checked_plot.set_ydata(check_coords_y[0:i])

            plt.draw()
            plt.pause(0.0001)
