"""Initial wave functions on the 2D grid.

Two shapes are supported via ``config.initial_values.wave_type``:

* ``gaussian_packet`` – a 2D Gaussian with independent sigma_x and sigma_y
* ``plane_wave``      – a wave train: uniform amplitude in y, super-Gaussian
                        envelope in x (so it actually propagates toward the
                        wall instead of filling the whole box from t = 0).

Both functions return a normalised complex array of shape ``(ny, nx)`` --
axis 0 is y, axis 1 is x, matching matplotlib's ``imshow`` with
``origin='lower'``.
"""

import numpy as np

from config import default_config


def _normalise(psi, dx, dy):
    norm = np.sqrt(np.sum(np.abs(psi) ** 2) * dx * dy)
    return psi / norm


def _gaussian_packet(iv):
    """ψ(x, y) = exp(i (px x + py y)) · exp(-((x-x0)/σx)² - ((y-y0)/σy)²)

    Note that σx and σy are not standard deviations: the standard deviation
    of |ψ|² along x is σx / 2 (and likewise in y).
    """
    x0, y0 = iv.initial_position
    px, py = iv.initial_momentum
    sx, sy = iv.sigma_x, iv.sigma_y

    X, Y = np.meshgrid(iv.x_grid, iv.y_grid, indexing='xy')
    envelope = np.exp(-((X - x0) / sx) ** 2 - ((Y - y0) / sy) ** 2)
    phase = np.exp(1j * (px * X + py * Y))
    return _normalise((phase * envelope).astype(complex), iv.dx, iv.dy)


def _plane_wave(iv):
    """A plane wave packet localised in x, uniform in y.

    ψ(x, y) = exp(i (px x + py y)) · exp(-((x - x0) / w)⁴)

    The super-Gaussian (4th power) envelope gives crisp leading/trailing
    edges instead of the soft Gaussian roll-off, so the wave looks like a
    coherent wave train rather than a packet.
    """
    x0, _ = iv.initial_position
    px, py = iv.initial_momentum
    w = iv.plane_wave_envelope_width

    X, Y = np.meshgrid(iv.x_grid, iv.y_grid, indexing='xy')
    envelope = np.exp(-((X - x0) / w) ** 4)
    phase = np.exp(1j * (px * X + py * Y))
    return _normalise((phase * envelope).astype(complex), iv.dx, iv.dy)


def get_wave_packet(config=default_config):
    """Build the initial wave function selected by ``config.initial_values.wave_type``."""
    iv = config.initial_values
    wave_type = getattr(iv, 'wave_type', 'gaussian_packet')

    if wave_type == 'gaussian_packet':
        return _gaussian_packet(iv)
    if wave_type == 'plane_wave':
        return _plane_wave(iv)

    raise ValueError(f"Unknown wave type: {wave_type}")
