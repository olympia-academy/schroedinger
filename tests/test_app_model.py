from dataclasses import replace
import json
import time

import numpy as np
import pytest

from schroedinger.app_jobs import JobManager
from schroedinger.app_model import (Experiment, boundary_details, calculate,
                                    frame_png, read_result, write_result)
from schroedinger.cli import configuration, parser
from schroedinger import get_barrier_mask, get_potential, get_wave_packet, simulate


def small_experiment():
    return Experiment(nx=48, ny=32, px=2.0, steps=3, frames=3)


def test_app_uses_the_same_propagation_as_cli():
    experiment = small_experiment()
    actual = calculate(experiment)
    config = configuration(parser().parse_args([
        "--nx", "48", "--ny", "32", "--px", "2", "--dt", "0.0390625", "--steps", "3", "--save-every", "2", "--no-progress"]))
    expected = simulate(get_wave_packet(config), get_potential(config), config, get_barrier_mask(config))
    assert np.array_equal(actual.densities, np.stack(expected.frames))
    assert np.array_equal(actual.times, expected.times)
    assert actual.summary["probability"] == expected.norms.tolist()


@pytest.mark.parametrize("method", ["crank_nicolson", "rk4"])
def test_app_1d_methods_and_portable_result_round_trip(tmp_path, method):
    experiment = replace(Experiment.defaults(1), method=method, nx=96, px=2.0,
                         dt=0.001, steps=5, frames=4)
    run = calculate(experiment)
    assert run.summary["solver"] == method
    assert run.densities.dtype == np.float32
    assert len(run.times) <= experiment.frames
    assert run.times[-1] == 0.005
    assert abs(run.summary["probability"][-1]-1) < 1e-9
    assert Experiment.read(run.configuration_json()) == experiment
    path = tmp_path/"run.npz"
    write_result(run, path)
    loaded = read_result(path)
    assert np.array_equal(loaded.densities, run.densities)
    assert loaded.summary == run.summary
    assert frame_png(loaded, 0).startswith(b"\x89PNG\r\n\x1a\n")


def test_discrete_opening_widths_and_resource_limits_are_visible():
    config = Experiment().configuration()
    details = boundary_details(config, get_barrier_mask(config))
    assert details["outer"] == "Dirichlet"
    assert details["opening_widths"] == pytest.approx([0.703125]*2)
    assert details["wall_faces"] == pytest.approx([-0.15625, 0.15625])
    with pytest.raises(ValueError, match="128 MiB"):
        replace(Experiment(), nx=1024, ny=1024, frames=121).configuration()
    with pytest.raises(ValueError, match="stability"):
        calculate(replace(Experiment.defaults(1), method="rk4", dt=100))
    with pytest.raises(ValueError):
        Experiment.read(json.dumps({"schema_version": 1, "experiment": {"unknown": 1}}))
    with pytest.raises(ValueError, match="8–2048"):
        Experiment.read(json.dumps({"schema_version": 1, "experiment": {"nx": 2}}))


def test_worker_lifecycle_collect_cancel_and_single_job():
    jobs = JobManager()
    try:
        identifier = jobs.start(small_experiment())
        deadline = time.monotonic()+25
        while jobs.status(identifier)["status"] == "running" and time.monotonic() < deadline:
            time.sleep(0.05)
        assert jobs.status(identifier)["status"] == "complete"
        run = jobs.collect(identifier)
        assert run.times[-1] == pytest.approx(3*0.0390625)
        assert not jobs.busy()
        identifier = jobs.start(replace(Experiment(), steps=100000, frames=2))
        with pytest.raises(ValueError, match="allerede"):
            jobs.start(small_experiment())
        jobs.cancel(identifier)
        assert not jobs.busy()
        assert jobs.status(identifier)["status"] == "expired"
    finally:
        jobs.close()
