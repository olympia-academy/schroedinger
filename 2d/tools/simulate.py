"""Split-step Fourier propagator for the 2D time-dependent Schrödinger equation.

Strang splitting:

    ψ(t + dt) ≈ U_V(dt/2) · U_T(dt) · U_V(dt/2) · ψ(t)

where U_V applies the potential phase exp(-i V dt / 2 ℏ) in real space and
U_T applies the kinetic phase exp(-i ℏ k² dt / 2 m) in Fourier space.

Each operator is unitary, so |ψ| is preserved up to FFT round-off — no manual
normalisation needed inside the loop.
"""

import numpy as np

from config import default_config

try:  # tqdm is nice-to-have; fall back to a no-op iterator if missing
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(it, **_):
        return it


def _kinetic_phase(config):
    """Pre-compute exp(-i ℏ (kx² + ky²) dt / 2m) on the FFT grid."""
    iv = config.initial_values
    m = config.constants.mass
    h_bar = config.constants.h_bar
    dt = iv.dt

    # numpy uses angular wavenumbers when scaled by 2π
    kx = 2 * np.pi * np.fft.fftfreq(iv.nx, d=iv.dx)
    ky = 2 * np.pi * np.fft.fftfreq(iv.ny, d=iv.dy)
    KX, KY = np.meshgrid(kx, ky, indexing='xy')
    k_squared = KX ** 2 + KY ** 2

    return np.exp(-1j * h_bar * k_squared * dt / (2.0 * m))


def _potential_half_phase(v, config):
    """exp(-i V dt / 2 ℏ) -- applied twice per step (Strang splitting)."""
    h_bar = config.constants.h_bar
    dt = config.initial_values.dt
    return np.exp(-1j * v * dt / (2.0 * h_bar))


def _absorbing_mask(config, width_frac=0.10):
    """Smooth multiplicative damping in a thin sponge layer near the edges.

    The split-step Fourier method uses periodic boundaries (FFT), so any wave
    that reaches an edge wraps around to the other side. We apply a sin² ramp
    that is *exactly* 1 across the interior and smoothly falls to 0 only
    inside the outermost ``width_frac`` fraction of each axis. This drains
    outgoing probability without dimming the simulation region of interest.
    """
    iv = config.initial_values

    def edge_profile(coord, lo, hi):
        L = hi - lo
        edge = width_frac * L
        d = np.minimum(coord - lo, hi - coord)  # distance to nearest edge
        ramp = np.sin(0.5 * np.pi * np.clip(d / edge, 0.0, 1.0)) ** 2
        return ramp

    mx = edge_profile(iv.x_grid, iv.x_min, iv.x_max)
    my = edge_profile(iv.y_grid, iv.y_min, iv.y_max)
    return np.outer(my, mx)  # shape (ny, nx)


def simulate(psi, v, config=default_config, barrier_mask=None):
    """Time-evolve ψ under the static potential V using split-step Fourier.

    Parameters
    ----------
    psi : (ny, nx) complex array
        Initial wave function.
    v : (ny, nx) real array
        Static potential.
    config : Config
        Simulation parameters.
    barrier_mask : (ny, nx) bool array or None
        Cells that should remain ψ ≡ 0 throughout the simulation. Used to
        realise an *infinite* barrier (Dirichlet hard wall) — the slit walls
        in the double- and single-slit scenarios.

    Returns
    -------
    list[(ny, nx) complex array]
        Snapshots saved every ``save_every`` steps (including t = 0).
    """
    steps = config.simulation_params.steps
    save_every = config.simulation_params.save_every

    half_V = _potential_half_phase(v, config)
    full_T = _kinetic_phase(config)
    absorber = _absorbing_mask(config)

    # Pre-compute the Dirichlet "keep" mask: 0 inside the impenetrable wall,
    # 1 elsewhere. Multiplying ψ by this each step enforces ψ ≡ 0 in the wall.
    if barrier_mask is not None:
        keep = (~barrier_mask).astype(float)
        psi = keep * psi  # also enforce on the initial state
    else:
        keep = None

    snapshots = [np.copy(psi)]

    for i in tqdm(range(steps), desc="2D Schrödinger"):
        # half potential kick
        psi = half_V * psi
        # full kinetic drift in k-space
        psi = np.fft.ifft2(full_T * np.fft.fft2(psi))
        # half potential kick
        psi = half_V * psi
        # enforce the impenetrable wall (V = +∞ inside it)
        if keep is not None:
            psi = keep * psi
        # drain whatever has reached the box edges (open-boundary approximation)
        psi = absorber * psi

        if (i + 1) % save_every == 0:
            snapshots.append(np.copy(psi))

    return snapshots
