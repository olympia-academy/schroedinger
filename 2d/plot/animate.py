from config import default_config
from schroedinger.visualization import animate as _animate

def animate(simulation, potential=None, barrier_mask=None, config=default_config,
            interval=40, vmax_percentile=99.5, vmax_skip_initial_frac=0.25):
    return _animate(simulation, config, potential, barrier_mask, interval,
                    vmax_percentile, vmax_skip_initial_frac)
