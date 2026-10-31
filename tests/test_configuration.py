from copy import deepcopy
import numpy as np
import pytest
from schroedinger import Config1D, Config2D, get_wave_packet, get_potential
from schroedinger.diagnostics import expectation


def test_grid_updates_recompute_spacing_and_automatic_dt(config2):
    config2.initial_values.dt = None
    old_dx = config2.initial_values.dx
    old_dt = config2.initial_values.dt
    config2.update("initial_values", nx=128, ny=96)
    assert get_wave_packet(config2).shape == (96, 128)
    assert config2.initial_values.dx == old_dx/2
    assert config2.initial_values.dt == old_dt/2


def test_explicit_dt_is_preserved_and_1d_grid_can_be_replaced(config1):
    config1.initial_values.dt = 0.001
    config1.update("initial_values", x_grid=np.linspace(-10, 10, 128))
    assert config1.initial_values.dx == pytest.approx(20/127)
    assert config1.initial_values.dt == 0.001


def test_configuration_updates_are_atomic(config2):
    original = deepcopy(config2.initial_values)
    with pytest.raises(ValueError):
        config2.update("initial_values", nx=128, ny=0)
    assert config2.initial_values.nx == original.nx
    with pytest.raises(AttributeError):
        config2.update("initial_values", typo=12)
    with pytest.raises(AttributeError):
        config2.update("simulation", steps=10)


def test_configurations_are_independent():
    a, b = Config2D(), Config2D()
    a.constants.mass = 3
    a.initial_values.nx = 128
    assert b.constants.mass == 10
    assert b.initial_values.nx == 512


@pytest.mark.parametrize("category,key,value", [
    ("constants", "mass", 0), ("constants", "h_bar", -1),
    ("initial_values", "nx", 0), ("initial_values", "ny", 4.5),
    ("initial_values", "dt", float("nan")),
    ("initial_values", "sigma_x", 0),
    ("simulation_params", "save_every", 0),
    ("simulation_params", "steps", -1),
    ("absorber", "width_frac", 0.5),
    ("absorber", "strength", -1),
])
def test_invalid_parameters_fail_early(config2, category, key, value):
    setattr(getattr(config2, category), key, value)
    with pytest.raises(ValueError):
        config2.validate()


def test_momentum_nyquist_validation(config2):
    config2.initial_values.initial_momentum = (100, 0)
    with pytest.raises(ValueError, match="Nyquist"):
        get_wave_packet(config2)


def test_states_use_physical_momentum_with_nonunit_hbar(config2):
    c = config2
    c.constants.h_bar = 2
    c.initial_values.initial_momentum = (3, 0)
    psi = get_wave_packet(c)
    kx = 2*np.pi*np.fft.fftfreq(c.initial_values.nx, c.initial_values.dx)
    def px(state):
        return np.fft.ifft(np.fft.fft(state, axis=1)*(c.constants.h_bar*kx), axis=1)
    assert expectation(psi, px, c.cell_volume) == pytest.approx(3, abs=1e-7)


@pytest.mark.parametrize("dimension", [1, 2])
def test_harmonic_potential_includes_mass(dimension):
    c = Config1D() if dimension == 1 else Config2D()
    c.constants.potential_type = "harmonic"
    c.constants.mass = 3
    c.barrier.omega = 2
    iv = c.initial_values
    r2 = iv.x_grid**2
    if dimension == 2:
        r2 = iv.y_grid[:, None]**2 + iv.x_grid[None, :]**2
    assert np.allclose(get_potential(c), 0.5*3*2**2*r2)
