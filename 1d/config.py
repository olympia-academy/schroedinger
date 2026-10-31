"""Compatibility imports; new code can import schroedinger.config directly."""
from schroedinger.config import Config1D as Config, Constants, Grid1D as InitialValues, SimulationParams as _SimulationParams

class SimulationParams(_SimulationParams):
    def __init__(self):
        super().__init__(steps=200000, save_every=2000)

default_config = Config()
