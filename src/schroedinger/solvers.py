"""Norm-preserving propagators and separately measured boundary absorption."""
from copy import deepcopy
import warnings
import numpy as np
from scipy.linalg.lapack import get_lapack_funcs
from tqdm import tqdm
from .config import Config1D, Config2D
from .diagnostics import normalize, probability
from .dirichlet import DirichletKinetic
from .results import SimulationResult


def laplacian1d(psi, dx):
    value = -2 * psi.copy()
    value[1:] += psi[:-1]
    value[:-1] += psi[1:]
    return value / dx**2


def rhs1d(psi, potential, config):
    c, iv = config.constants, config.initial_values
    return 1j*c.h_bar/(2*c.mass) * laplacian1d(psi, iv.dx) - 1j*potential*psi/c.h_bar


def rk4_step(psi, dt, potential, config):
    k1 = rhs1d(psi, potential, config)
    k2 = rhs1d(psi + dt*k1/2, potential, config)
    k3 = rhs1d(psi + dt*k2/2, potential, config)
    k4 = rhs1d(psi + dt*k3, potential, config)
    return psi + dt*(k1 + 2*k2 + 2*k3 + k4)/6


def _crank_nicolson(potential, config):
    """Factor the constant tridiagonal left-hand side once."""
    c, iv = config.constants, config.initial_values
    kinetic_off = -c.h_bar**2 / (2*c.mass*iv.dx**2)
    h_diagonal = -2*kinetic_off + potential
    factor = 1j * iv.dt / (2*c.h_bar)
    off_a = np.full(iv.nx-1, factor*kinetic_off, dtype=complex)
    diag_a = np.asarray(1 + factor*h_diagonal, dtype=complex)
    gttrf, gttrs = get_lapack_funcs(("gttrf", "gttrs"), (diag_a,))
    dl, diagonal, du, du2, pivots, info = gttrf(off_a.copy(), diag_a, off_a.copy())
    if info:
        raise RuntimeError(f"Crank-Nicolson factorization failed: {info}")
    diag_b = 1 - factor*h_diagonal
    off_b = -factor*kinetic_off

    def step(psi):
        right = diag_b*psi
        right[1:] += off_b*psi[:-1]
        right[:-1] += off_b*psi[1:]
        evolved, info = gttrs(dl, diagonal, du, du2, pivots, right[:, None])
        if info:
            raise RuntimeError(f"Crank-Nicolson solve failed: {info}")
        return evolved[:, 0]
    return step


def kinetic_phase(config):
    iv, c = config.initial_values, config.constants
    kx = 2*np.pi*np.fft.fftfreq(iv.nx, d=iv.dx)
    ky = 2*np.pi*np.fft.fftfreq(iv.ny, d=iv.dy)
    return np.exp(-1j*c.h_bar*iv.dt*(ky[:, None]**2 + kx[None, :]**2)/(2*c.mass))


def absorbing_rate(config):
    """A fixed decay rate gamma(x), independent of time-step subdivision."""
    iv, absorber = config.initial_values, config.absorber
    shape = (iv.nx,) if config.dimension == 1 else (iv.ny, iv.nx)
    if not absorber.enabled or absorber.strength == 0:
        return np.zeros(shape)

    def profile(grid, lo, hi):
        distance = np.minimum(grid-lo, hi-grid)
        ramp = np.clip(1-distance / ((hi-lo)*absorber.width_frac), 0, 1)
        return absorber.strength * np.sin(np.pi*ramp/2)**2

    rate = profile(iv.x_grid, iv.x_min, iv.x_max)
    if config.dimension == 2:
        rate = rate[None, :] + profile(iv.y_grid, iv.y_min, iv.y_max)[:, None]
    return rate


def simulate(psi, v=0, config=None, barrier_mask=None):
    """Return saved frames, times, norms and the probability absorbed at edges.

    Hard walls use directional sine propagation; finite 2D potentials use
    Fourier propagation. 1D defaults to Crank-Nicolson, with RK4 available
    for comparison. The initial state is normalized once, never in the loop.
    """
    if config is None:
        config = Config1D() if np.ndim(psi) == 1 else Config2D()
    config = deepcopy(config)
    config.validate()
    iv, sp, c = config.initial_values, config.simulation_params, config.constants
    shape = (iv.nx,) if config.dimension == 1 else (iv.ny, iv.nx)
    if np.shape(psi) != shape:
        raise ValueError(f"Expected wave-function shape {shape}, got {np.shape(psi)}")
    raw_v = np.asarray(v)
    if np.iscomplexobj(raw_v) or not np.isfinite(raw_v).all():
        raise ValueError("Potential must be finite and real; use barrier_mask for hard walls")
    potential = np.broadcast_to(np.asarray(v, dtype=float), shape)
    psi = normalize(np.array(psi, dtype=complex, copy=True), config.cell_volume)
    projection_loss = 0.0
    if barrier_mask is not None:
        if config.dimension != 2 or np.shape(barrier_mask) != shape:
            raise ValueError("barrier_mask must match a 2D wave-function grid")
        barrier_mask = np.array(barrier_mask, dtype=bool, copy=True)
        psi[barrier_mask] = 0
        projection_loss = max(0.0, 1-probability(psi, config.cell_volume))
        if projection_loss > 1e-10:
            warnings.warn(f"Initial state overlaps the wall by {projection_loss:.3%}; "
                          "projecting and normalizing once before t=0", RuntimeWarning, stacklevel=2)
        psi = normalize(psi, config.cell_volume)

    if config.dimension == 1:
        if sp.method == "rk4":
            bound = 2*c.h_bar/(c.mass*iv.dx**2) + np.max(np.abs(potential))/c.h_bar
            if iv.dt*bound > np.sqrt(8):
                raise ValueError("RK4 time step exceeds its stability bound; reduce dt or use crank_nicolson")
            unitary_step = lambda state: rk4_step(state, iv.dt, potential, config)
            solver = "rk4"
        else:
            unitary_step = _crank_nicolson(potential, config)
            solver = "crank_nicolson"
    else:
        half_v = np.exp(-1j*potential*iv.dt/(2*c.h_bar))
        if barrier_mask is None:
            phase = kinetic_phase(config)
            drift = lambda state: np.fft.ifft2(phase*np.fft.fft2(state))
            solver = "fourier_strang"
        else:
            drift = DirichletKinetic(barrier_mask, config).step
            solver = "dirichlet_sine_strang"

        def unitary_step(state):
            return half_v * drift(half_v * state)

    rate = absorbing_rate(config)
    damping = np.exp(-rate*iv.dt/2) if np.any(rate) else None
    absorbed = 0.0
    frames, times, norms, losses = [], [], [], []

    def save(step):
        norm = probability(psi, config.cell_volume)
        if not np.isfinite(norm) or not np.isfinite(psi).all():
            raise FloatingPointError("Non-finite wave function; reduce the time step")
        frames.append((np.abs(psi)**2).astype(np.float32) if sp.store_density else psi.copy())
        times.append(step*iv.dt)
        norms.append(norm)
        losses.append(absorbed)

    def damp(state):
        before = probability(state, config.cell_volume)
        state = damping * state
        removed = before - probability(state, config.cell_volume)
        return state, max(0.0, removed)

    save(0)
    for step in tqdm(range(1, sp.steps+1), desc=f"{config.dimension}D Schrodinger", disable=not sp.progress):
        if damping is not None:
            psi, lost = damp(psi)
            absorbed += lost
        psi = unitary_step(psi)
        if damping is not None:
            psi, lost = damp(psi)
            absorbed += lost
        if step % sp.save_every == 0 or step == sp.steps:
            save(step)

    return SimulationResult(frames, np.asarray(times), np.asarray(norms),
                            np.asarray(losses), sp.store_density, solver, projection_loss)
