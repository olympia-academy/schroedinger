"""Legacy API backed by the shared, tested solver."""
from config import default_config
from schroedinger.solvers import simulate as _simulate

def simulate(psi, v, config=default_config, barrier_mask=None):
    return _simulate(psi, v, config, barrier_mask)
