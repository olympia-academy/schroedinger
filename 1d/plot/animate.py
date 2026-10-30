from config import default_config
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np


def complex_plot(y, config=default_config,  **kwargs):
    initial_values = config.initial_values
    x = initial_values.x_grid
    real = np.real(y)
    imag = np.imag(y)
    a, *_ = plt.plot(x, real, label='Re', **kwargs)
    b,  *_ = plt.plot(x, imag, label='Im', **kwargs)
    plt.xlim(min(x), max(x))
    abs_y = np.abs(y)
    p, *_ = plt.plot(x, abs_y, label=r'$\sqrt{P}$')
    plt.legend()

    return a, b, p


def animate(simulation, init_func=None, config=default_config):
    initial_values = config.initial_values
    x = initial_values.x_grid
    fig = plt.figure()
    re, im, prob = complex_plot(y=simulation[0], config=config)
    plt.xlim(min(x)-1, max(x)+1)
    plt.ylim(-2, 2)
    plt.axvspan(5.0, 5.5, alpha=0.2, color='orange')

    if init_func: # TODO: NOT YET USED
        init_func()
        plt.legend()

    def update_frame(frame):
        y = simulation[frame]
        re.set_data((x, np.real(y)))
        im.set_data((x, np.imag(y)))
        abs_y = np.abs(y)
        prob_density = abs_y
        mean_pos = np.sum(x * prob_density) / np.sum(prob_density)
        x_loc = np.argmin(np.abs(x - mean_pos))
        prob.set_data(x, abs_y)

        return prob, re, im

    anim = FuncAnimation(fig, update_frame, frames=int(len(simulation)), interval=50)
    plt.show()

    return
