from dataclasses import replace
import io

import numpy as np
import pytest

from schroedinger.wavepacket import position_moments, free_gaussian_moments, gaussian_outside_probability
from schroedinger.app_wavepacket import analyze_free_packet
from schroedinger.app_presets import preset
from schroedinger.app_model import calculate, read_result, write_result


def test_moments_recover_translated_gaussian_and_are_conditional_on_probability():
    x = np.linspace(90, 110, 2001)
    density = np.exp(-0.5*((x-101)/0.7)**2)/(np.sqrt(2*np.pi)*0.7)
    actual = position_moments(np.array([density, 0.2*density, np.zeros_like(density)]), x)
    np.testing.assert_allclose(actual["probability"][:2], [1, 0.2], atol=1e-12)
    np.testing.assert_allclose(actual["mean_x"][:2], 101, atol=1e-12)
    np.testing.assert_allclose(actual["sigma_x"][:2], 0.7, atol=1e-12)
    assert np.isnan(actual["mean_x"][-1]) and np.isnan(actual["sigma_x"][-1])


@pytest.mark.parametrize("case", ["negative", "nan", "complex", "shape", "grid"])
def test_moments_reject_invalid_inputs(case):
    x, densities = np.arange(8, dtype=float), np.ones((2, 8))
    if case == "negative": densities[0, 0] = -1
    if case == "nan": densities[0, 0] = np.nan
    if case == "complex": densities = densities.astype(complex)
    if case == "shape": densities = densities[:, :-1]
    if case == "grid": x[3] += 0.3
    with pytest.raises(ValueError):
        position_moments(densities, x)


def test_reference_uses_standard_deviation_and_nonunit_mass_and_hbar():
    reference = free_gaussian_moments([0, 2], x0=1, p0=-3, sigma0=0.5, mass=2, hbar=3)
    np.testing.assert_allclose(reference["mean_x"], [1, -2])
    np.testing.assert_allclose(reference["sigma_x"], [0.5, np.sqrt(0.25+9)])
    tail = gaussian_outside_probability(np.array([0, 10]), np.array([1, 1]), -5, 5)
    assert tail[0] == pytest.approx(5.73303143758e-7)
    assert tail[1] > 0.99999


@pytest.mark.parametrize("values", [{"sigma0": 0}, {"hbar": 0}, {"mass": -1}, {"p0": np.nan}])
def test_invalid_reference_parameters_are_rejected(values):
    params = dict(x0=0, p0=1, sigma0=1, mass=1, hbar=1)
    params.update(values)
    with pytest.raises(ValueError):
        free_gaussian_moments([0, 1], **params)


def test_default_reference_is_accurate_and_grid_refinement_reduces_error():
    experiment = preset("free_reference")
    run = calculate(experiment)
    coarse = analyze_free_packet(run)
    fine = analyze_free_packet(calculate(replace(experiment, nx=2*(experiment.nx-1)+1)))
    assert coarse["summary"]["reference_usable"]
    assert coarse["summary"]["initial_position_std"] == 1
    assert coarse["summary"]["max_reference_outside_probability"] < 1e-12
    assert coarse["summary"]["max_probability_drift"] < 1e-10
    assert coarse["summary"]["max_mean_error"] < 0.002
    assert coarse["summary"]["max_sigma_error"] < 0.001
    for field in ("max_mean_error", "max_sigma_error"):
        assert fine["summary"][field] < 0.35*coarse["summary"][field]
    assert coarse["reference"]["mean_x"][-1] == 0
    assert coarse["reference"]["sigma_x"][-1] == pytest.approx(np.sqrt(2))


@pytest.mark.parametrize("method", ["crank_nicolson", "rk4"])
def test_reverse_packet_nonunit_constants_follow_the_reference(method):
    experiment = replace(preset("free_reference"), method=method, nx=512,
                         mass=2, hbar=2, px=-1, x0=2, dt=0.0005, steps=400)
    summary = analyze_free_packet(calculate(experiment))["summary"]
    assert summary["reference_usable"]
    assert summary["max_mean_error"] < 0.0002
    assert summary["max_sigma_error"] < 0.0002


def test_analysis_reopens_old_result_format_without_propagation_or_mutation(monkeypatch):
    run = calculate(replace(preset("free_reference"), steps=20))
    buffer = io.BytesIO()
    write_result(run, buffer)
    buffer.seek(0)
    loaded = read_result(buffer)
    before = loaded.densities.copy()
    def forbidden(*args, **kwargs):
        pytest.fail("Analysis of stored densities must not propagate")
    monkeypatch.setattr("schroedinger.app_model.simulate", forbidden)
    analysis = analyze_free_packet(loaded)
    assert analysis["summary"]["reference_usable"]
    np.testing.assert_array_equal(before, loaded.densities)


@pytest.mark.parametrize("changes", [{"absorber": True}, {"steps": 8000}, {"x0": -11.5}])
def test_reference_comparison_is_disabled_when_its_assumptions_fail(changes):
    # The eligibility check uses the entire saved time history, not just the endpoint.
    experiment = replace(preset("free_reference"), steps=2, **{key: value for key, value in changes.items() if key != "steps"})
    run = calculate(experiment)
    if "steps" in changes:
        run.experiment.steps = changes["steps"]
        run.summary["times"][-1] = run.experiment.steps*run.experiment.dt
    summary = analyze_free_packet(run)["summary"]
    assert not summary["reference_usable"]
    assert summary["reasons"]
    assert "max_mean_error" not in summary
