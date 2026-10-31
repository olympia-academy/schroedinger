from config import default_config
from schroedinger.potentials import get_potential as _get_potential, get_barrier_mask as _get_barrier_mask

def get_potential(config=default_config):
    return _get_potential(config)

def get_barrier_mask(config=default_config):
    return _get_barrier_mask(config)
