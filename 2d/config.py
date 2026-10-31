"""Compatibility imports; new code can import schroedinger.config directly."""
from schroedinger.config import Config2D as Config, Constants as _Constants, Grid2D as InitialValues, SimulationParams, Barrier2D as BarrierGeometry

class Constants(_Constants):
    def __init__(self):
        super().__init__(potential_strength=22.0, potential_type="double_slit")

default_config = Config()
