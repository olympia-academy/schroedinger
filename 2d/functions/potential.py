"""2D static potentials and impenetrable-barrier masks.

The two slit scenarios — ``'double_slit'`` and ``'single_slit'`` — model the
wall as a *true infinite barrier*: the potential is V = 0 everywhere and the
impenetrable region is enforced by a Dirichlet mask in the time-evolution
loop (ψ ≡ 0 inside the wall on every step). This is mathematically
equivalent to V = +∞ in the wall and gives **zero tunneling** through the
barrier — only the slit openings let probability through.

The ``'wall'`` scenario is kept around for tunneling demonstrations and uses
a *finite* potential of strength ``config.constants.potential_strength``.
``'free'`` is just V ≡ 0 with no mask.

Each function returns an array of shape ``(ny, nx)`` matching the wave-packet
convention.
"""

import numpy as np

from config import default_config


def _wall_slab(X, barrier_x, thickness):
    """Boolean mask of the vertical wall slab."""
    half = thickness / 2.0
    return (X >= barrier_x - half) & (X <= barrier_x + half)


def _slit_open_region(Y, kind, bg):
    """Boolean mask of the *open* region inside the wall (where ψ may flow).

    Returns False for the 'wall' / 'free' case (no openings).
    """
    if kind == 'single_slit':
        return np.abs(Y) <= bg.slit_width / 2.0
    if kind == 'double_slit':
        half_w = bg.slit_width / 2.0
        centre = bg.slit_separation / 2.0
        upper = (Y >= centre - half_w) & (Y <= centre + half_w)
        lower = (Y >= -centre - half_w) & (Y <= -centre + half_w)
        return upper | lower
    return np.zeros_like(Y, dtype=bool)


def get_potential(config=default_config):
    """Return the static potential V(x, y).

    V is identically zero for the ``'free'``, ``'double_slit'`` and
    ``'single_slit'`` scenarios — the slit walls are enforced via
    :func:`get_barrier_mask` instead.
    """
    iv = config.initial_values
    bg = config.barrier
    v0 = config.constants.potential_strength
    kind = config.constants.potential_type

    X, Y = np.meshgrid(iv.x_grid, iv.y_grid, indexing='xy')
    V = np.zeros_like(X)

    if kind in ('free', 'double_slit', 'single_slit'):
        return V

    if kind == 'wall':
        wall = _wall_slab(X, bg.barrier_x, bg.barrier_thickness)
        V[wall] = v0
        return V

    raise ValueError(f"Unknown potential type: {kind}")


def get_barrier_mask(config=default_config):
    """Return a boolean ``(ny, nx)`` array of the impenetrable wall.

    ``True`` cells are forced to ψ = 0 every step (Dirichlet hard wall) —
    that's how we realise V = +∞ inside the wall without baking a giant
    finite number into the potential. Returns ``None`` for scenarios that
    have no hard wall (``'free'`` and ``'wall'`` — the latter uses finite V
    so tunneling is allowed).
    """
    iv = config.initial_values
    bg = config.barrier
    kind = config.constants.potential_type

    if kind in ('free', 'wall'):
        return None

    X, Y = np.meshgrid(iv.x_grid, iv.y_grid, indexing='xy')
    wall = _wall_slab(X, bg.barrier_x, bg.barrier_thickness)
    open_region = _slit_open_region(Y, kind, bg)
    return wall & ~open_region
