"""Heatmap animation of the 2D probability density.

Uses matplotlib's ``imshow`` for fast updates and overlays the static barrier
as a faint contour so the slits are visible against the wave packet.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation

from config import default_config


def _density(psi):
    return np.abs(psi) ** 2


def animate(simulation, potential=None, barrier_mask=None,
            config=default_config, interval=40,
            vmax_percentile=99.5, vmax_skip_initial_frac=0.25):
    """Animate |ψ|² as a heatmap with the wall overlaid.

    Pass ``potential`` (a finite-V wall, e.g. for tunneling) and/or
    ``barrier_mask`` (a Dirichlet hard wall, e.g. for slit scenarios) — the
    overlay uses whichever one is non-trivial.

    The colour scale is chosen from the *post-impact* portion of the
    trajectory and from a high percentile rather than the absolute max, so
    the diffraction / interference fringes downstream of the slits stay
    visible instead of being washed out by the initial sharp peak.
    """
    iv = config.initial_values

    extent = (iv.x_min, iv.x_max, iv.y_min, iv.y_max)

    densities = [_density(frame) for frame in simulation]

    skip = max(1, int(len(densities) * vmax_skip_initial_frac))
    tail_stack = np.stack(densities[skip:]) if len(densities) > skip else np.stack(densities)
    vmax = float(np.percentile(tail_stack, vmax_percentile))
    if vmax <= 0:  # degenerate fallback
        vmax = float(max(d.max() for d in densities))

    fig, ax = plt.subplots(figsize=(9, 5))
    im = ax.imshow(
        densities[0],
        extent=extent,
        origin='lower',
        cmap='inferno',
        vmin=0.0,
        vmax=vmax,
        interpolation='bilinear',
        aspect='auto',
    )

    # Wall overlay: prefer the explicit barrier mask (used by slit scenarios
    # where V is identically zero) and fall back to a contour of V.
    if barrier_mask is not None and barrier_mask.any():
        ax.contour(
            iv.x_grid, iv.y_grid, barrier_mask.astype(float),
            levels=[0.5], colors='white', linewidths=0.8, alpha=0.8,
        )
    elif potential is not None:
        v0 = config.constants.potential_strength
        if v0 > 0 and potential.max() > 0:
            ax.contour(
                iv.x_grid, iv.y_grid, potential,
                levels=[v0 * 0.5],
                colors='white', linewidths=0.8, alpha=0.7,
            )

    ax.set_xlabel('x')
    ax.set_ylabel('y')
    title = ax.set_title(r'$|\psi(x, y, t)|^2$    frame 0 / {}'.format(len(simulation) - 1))
    fig.colorbar(im, ax=ax, label=r'$|\psi|^2$')

    def update(frame):
        im.set_data(densities[frame])
        title.set_text(r'$|\psi(x, y, t)|^2$    frame {} / {}'.format(frame, len(simulation) - 1))
        return im, title

    anim = FuncAnimation(
        fig, update, frames=len(simulation), interval=interval, blit=False
    )

    plt.tight_layout()
    plt.show()
    return anim
