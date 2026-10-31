"""Keep the independent teaching calculation consistent with the package."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from schroedinger import Config1D, get_wave_packet, simulate
from schroedinger.diagnostics import expectation


def example(name):
    path = Path(__file__).resolve().parents[1] / "examples" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("method", ["crank_nicolson", "rk4"])
def test_independent_teaching_method_matches_production(tmp_path, method):
    teaching = example("compare_1d_methods")
    report = teaching.compare(method=method, output=tmp_path)
    config = Config1D()
    config.constants.mass = 1
    config.constants.potential_type = "free"
    iv = config.initial_values
    iv.nx = 201
    iv.initial_position = -3
    iv.initial_momentum = 2
    iv.dt = report["dt"]
    sp = config.simulation_params
    sp.method = method
    sp.steps = sp.save_every = report["steps"]
    sp.progress = False
    result = simulate(get_wave_packet(config), 0, config)
    measured = report["methods"][method]
    assert measured["probability"] == pytest.approx(result.norms[-1], abs=2e-12)
    assert measured["mean_x"] == pytest.approx(
        expectation(result[-1], iv.x_grid, config.cell_volume), abs=2e-12)
    # A continuum check is separate: this deliberately small grid has space error.
    assert abs(measured["mean_x"]-report["continuum_mean_x"]) < 0.03


def test_screen_comparison_removes_uniform_y_normalization_and_keeps_region_fixed():
    study = example("double_slit_sensitivity")
    profiles = []
    for case in ("baseline", "larger_box"):
        config = study.configuration(study.CASES[case])
        iv = config.initial_values
        x, y = np.meshgrid(iv.x_grid, iv.y_grid)
        length_y = iv.y_max-iv.y_min
        incoming = np.exp(-((iv.x_grid+8)/2)**2)
        incoming /= incoming.sum()*iv.dx
        initial = np.broadcast_to(incoming/length_y, x.shape)
        final = 0.2*np.exp(-(x-6)**2)*np.cos(y)**2/length_y
        result = SimpleNamespace(density=lambda index: {0: initial, -1: final}[index])
        positions, profile, incident = study.screen_profile(result, config)
        assert positions[0] == -6 and positions[-1] == 6
        assert incident == pytest.approx(1/length_y)
        profiles.append(profile)
    assert np.allclose(profiles[0], profiles[1], atol=1e-12)
