"""Normalized states; momentum phases consistently use p*x/hbar."""
import numpy as np
from .diagnostics import normalize


def get_wave_packet(config):
    config.validate()
    iv, hbar = config.initial_values, config.constants.h_bar
    if config.dimension == 1:
        x = iv.x_grid
        psi = np.exp(1j * iv.initial_momentum * x / hbar) * np.exp(
            -((x - iv.initial_position) / iv.initial_position_uncertainty)**2)
    else:
        x, y = np.meshgrid(iv.x_grid, iv.y_grid, indexing="xy")
        x0, y0 = iv.initial_position
        px, py = iv.initial_momentum
        if iv.wave_type == "gaussian_packet":
            envelope = np.exp(-((x - x0) / iv.sigma_x)**2 - ((y - y0) / iv.sigma_y)**2)
        else:
            envelope = np.exp(-((x - x0) / iv.plane_wave_envelope_width)**4)
        psi = np.exp(1j * (px*x + py*y) / hbar) * envelope
    return normalize(psi, config.cell_volume)
