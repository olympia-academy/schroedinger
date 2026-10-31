from config import default_config
from schroedinger.visualization import animate as _animate
import matplotlib.pyplot as plt
import numpy as np

def complex_plot(y, config=default_config, **kwargs):
    x = config.initial_values.x_grid
    real, = plt.plot(x, np.real(y), label="Re", **kwargs)
    imag, = plt.plot(x, np.imag(y), label="Im", **kwargs)
    density, = plt.plot(x, np.abs(y)**2, label=r"$|\psi|^2$")
    plt.legend()
    return real, imag, density

def animate(simulation, init_func=None, config=default_config, potential=None):
    if init_func is not None:
        init_func()
    return _animate(simulation, config, potential=potential)
