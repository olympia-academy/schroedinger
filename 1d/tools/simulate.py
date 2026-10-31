"""Legacy API backed by the shared, tested solver."""
from config import default_config
from schroedinger.solvers import simulate as _simulate, laplacian1d, rhs1d, rk4_step
from schroedinger.diagnostics import normalize as _normalize

def normalize(f, config=default_config):
    return _normalize(f, config.cell_volume)

def d_dx2(f, config=default_config):
    return laplacian1d(f, config.initial_values.dx)

def hamiltonian(phi, v=0, config=default_config):
    return rhs1d(phi, v, config)

def rk4(phi, dt, v=0, config=default_config):
    return rk4_step(phi, dt, v, config)

def simulate(psi, v=0, config=default_config):
    return _simulate(psi, v, config)
