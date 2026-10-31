import os
from pathlib import Path
import pytest

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".mpl-cache"))

from schroedinger import Config1D, Config2D


@pytest.fixture
def config1():
    c = Config1D()
    c.initial_values.nx = 256
    c.initial_values.initial_momentum = 2.0
    c.constants.mass = 1.0
    c.constants.potential_type = "free"
    c.simulation_params.steps = 40
    c.simulation_params.save_every = 10
    c.simulation_params.progress = False
    return c


@pytest.fixture
def config2():
    c = Config2D()
    iv = c.initial_values
    iv.nx, iv.ny = 64, 48
    iv.x_min, iv.x_max = -8.0, 8.0
    iv.y_min, iv.y_max = -6.0, 6.0
    iv.initial_position = (-3.0, 0.0)
    iv.initial_momentum = (2.0, 0.0)
    iv.dt = 0.02
    c.constants.mass = 1.0
    c.constants.potential_type = "free"
    c.simulation_params.steps = 20
    c.simulation_params.save_every = 5
    c.simulation_params.progress = False
    c.absorber.enabled = False
    return c
