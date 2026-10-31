"""Progress follows real solver steps and survives incomplete status reads."""
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from schroedinger.app_model import Experiment, calculate
from schroedinger.app_worker import ProgressReporter
from schroedinger.app_jobs import JobManager


@pytest.mark.parametrize("variant", ["cn", "rk4", "fourier", "dirichlet"])
def test_progress_reports_all_completed_steps_without_changing_results(variant):
    if variant in {"cn", "rk4"}:
        experiment = replace(Experiment.defaults(1), nx=48, steps=7, frames=3, px=2,
                             method="rk4" if variant == "rk4" else "crank_nicolson", dt=0.001)
    else:
        experiment = Experiment(nx=48, ny=32, steps=7, frames=3, px=2,
                                scenario="free" if variant == "fourier" else "double_slit")
    updates = []
    actual = calculate(experiment, progress_callback=lambda step, total: updates.append((step, total)))
    expected = calculate(experiment)
    assert updates == [(step, 7) for step in range(8)]
    assert len(actual.times) < len(updates)  # Propagation steps, not saved frames.
    np.testing.assert_array_equal(actual.densities, expected.densities)
    assert actual.summary == expected.summary


def test_progress_file_throttles_updates_and_forces_final_saving_state(tmp_path):
    moments = iter([0, 0.1, 0.25, 0.26, 0.27])
    reporter = ProgressReporter(tmp_path, clock=lambda: next(moments))
    reporter(0, 10)
    reporter(1, 10)
    assert json.loads((tmp_path/"progress.json").read_text())["completed_steps"] == 0
    reporter(2, 10)
    assert json.loads((tmp_path/"progress.json").read_text())["completed_steps"] == 2
    reporter(10, 10)
    reporter(10, 10, "saving")
    assert json.loads((tmp_path/"progress.json").read_text()) == {
        "completed_steps": 10, "total_steps": 10, "stage": "saving"}
    assert not (tmp_path/"progress.tmp").exists()


def test_busy_progress_file_does_not_fail_a_calculation(tmp_path, monkeypatch):
    reporter = ProgressReporter(tmp_path)
    monkeypatch.setattr(Path, "replace", lambda *args: (_ for _ in ()).throw(PermissionError("busy")))
    reporter(1, 10)  # A monitoring failure must not become a numerical failure.


def test_manager_keeps_last_progress_when_snapshot_is_incomplete(tmp_path):
    from types import SimpleNamespace
    jobs = JobManager()
    try:
        jobs.process = SimpleNamespace(poll=lambda: None)
        jobs.directory = SimpleNamespace(name=str(tmp_path))
        jobs.identifier, jobs.started = "test", 0
        jobs.progress = {"completed_steps": 0, "total_steps": 10, "stage": "starting"}
        assert jobs.status("test")["completed_steps"] == 0
        (tmp_path/"progress.json").write_text(json.dumps({"completed_steps": 4, "total_steps": 10, "stage": "computing"}))
        assert jobs.status("test")["completed_steps"] == 4
        (tmp_path/"progress.json").write_text('{"completed_steps":')
        assert jobs.status("test")["completed_steps"] == 4
        (tmp_path/"progress.json").write_text(json.dumps({"completed_steps": 2, "total_steps": 10, "stage": "computing"}))
        assert jobs.status("test")["completed_steps"] == 4
    finally:
        jobs.process = jobs.directory = jobs.identifier = None
        jobs.close()
