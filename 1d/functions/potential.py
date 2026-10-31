from config import default_config
from schroedinger.potentials import get_potential as _get_potential

def get_potential(config=default_config, **kwargs):
    return _get_potential(config, **kwargs)


