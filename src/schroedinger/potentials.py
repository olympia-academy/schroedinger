"""Finite scalar potentials and excluded Dirichlet wall cells."""
import numpy as np


def _slab(x, barrier):
    return np.abs(x - barrier.barrier_x) <= barrier.barrier_thickness / 2


def get_potential(config, **kwargs):
    config.validate()
    iv, c, bg = config.initial_values, config.constants, config.barrier
    kind, v0 = c.potential_type, c.potential_strength
    if config.dimension == 1:
        x = iv.x_grid
        a, b, d = kwargs.get("a", bg.a), kwargs.get("b", bg.b), kwargs.get("d", bg.d)
        if kind == "free":
            return np.zeros_like(x)
        if kind == "square_well":
            return np.where((x > a) & (x < b), 0.0, v0)
        if kind == "square_wall":
            return np.where(((a-d <= x) & (x <= a)) | ((b <= x) & (x <= b+d)), v0, 0.0)
        if kind == "power":
            return v0 * np.abs(x)**kwargs.get("n", bg.n)
        return 0.5 * c.mass * bg.omega**2 * x**2
    x, y = np.meshgrid(iv.x_grid, iv.y_grid, indexing="xy")
    v = np.zeros_like(x)
    if kind == "wall":
        wall = _slab(x, bg)
        if not wall.any():
            raise ValueError("The wall is outside the box or not resolved by the grid")
        v[wall] = v0
    elif kind == "harmonic":
        v = 0.5 * c.mass * bg.omega**2 * (x*x + y*y)
    return v


def get_barrier_mask(config):
    config.validate()
    if config.dimension == 1 or config.constants.potential_type not in {"single_slit", "double_slit"}:
        return None
    iv, bg = config.initial_values, config.barrier
    x, y = np.meshgrid(iv.x_grid, iv.y_grid, indexing="xy")
    wall = _slab(x, bg)
    if config.constants.potential_type == "single_slit":
        opening = np.abs(y) <= bg.slit_width / 2
    else:
        opening = (np.abs(y-bg.slit_separation/2) <= bg.slit_width/2) | (
            np.abs(y+bg.slit_separation/2) <= bg.slit_width/2)
    if not wall.any() or not (wall & opening).any() or not (wall & ~opening).any():
        raise ValueError("Wall and slit openings must both be resolved inside the grid")
    return wall & ~opening
