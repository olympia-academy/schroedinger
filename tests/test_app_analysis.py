from dataclasses import replace
import io
import json
from zipfile import ZipFile

import numpy as np
import pytest

from schroedinger.app_analysis import measurements, nearest_indices, refined_experiment, density_difference
from schroedinger.app_model import Experiment, RunData, boundary_details, calculate, read_result, write_result
from schroedinger.app_playback import prepare_group
from schroedinger.potentials import get_barrier_mask


def synthetic(experiment, value=None):
    config = experiment.configuration()
    iv = config.initial_values
    shape = (2, iv.ny, iv.nx) if experiment.dimension == 2 else (2, iv.nx)
    density = np.full(shape, value if value is not None else 1/(np.prod(shape[1:])*config.cell_volume), dtype=np.float32)
    norm = density.sum(axis=tuple(range(1, density.ndim)), dtype=float)*config.cell_volume
    summary = {"times": [0, experiment.dt*experiment.steps], "probability": norm.tolist(),
               "absorbed_probability": [0, 0], "solver": "test", "max_probability_budget_error": 0,
               "boundaries": boundary_details(config, get_barrier_mask(config))}
    return RunData(experiment, density, summary)


def test_nearest_frames_clamp_and_ties_are_earlier():
    assert nearest_indices([0, 2, 5], [-1, 1, 1.9, 3.5, 6]).tolist() == [0, 0, 1, 1, 2]


@pytest.mark.parametrize("dimension", [1, 2])
def test_regions_partition_density_and_profile_is_actual_grid_column(dimension):
    experiment = replace(Experiment.defaults(dimension), nx=48, ny=32, steps=2, px=2)
    run = synthetic(experiment)
    actual = measurements(run)
    np.testing.assert_allclose(np.array(list(actual["regions"].values())).sum(axis=0), run.summary["probability"])
    if dimension == 2:
        grid = experiment.configuration().initial_values.x_grid
        index = np.argmin(abs(grid-actual["screen_x"]))
        np.testing.assert_array_equal(actual["profile"], run.densities[:, :, index])
        assert actual["screen_x"] == grid[index]


def test_comparison_keeps_one_scale_all_times_and_independent_saved_frame_indices():
    a = synthetic(Experiment(nx=48, ny=32, px=2, steps=4, frames=3), value=0.01)
    b = synthetic(replace(a.experiment, frames=5), value=0.02)
    b.densities = np.repeat(b.densities[:1], 3, axis=0)
    b.summary.update(times=[0, a.times[-1]*0.6, a.times[-1]], probability=[b.summary["probability"][0]]*3,
                     absorbed_probability=[0]*3)
    payload = prepare_group([{"id": "a", "name": "A", "run": a}, {"id": "b", "name": "B", "run": b}])
    first, second = payload["runs"]
    assert first["vmax"] == second["vmax"]
    assert first["palette"] == second["palette"]
    assert first["profile_max"] == second["profile_max"]
    assert first["indices"] == [0, 0, 1]
    assert second["indices"] == [0, 1, 2]
    assert payload["times"][-1] == a.times[-1]


@pytest.mark.parametrize("dimension", [1, 2])
def test_refinement_keeps_time_and_refines_actual_grid(dimension):
    experiment = Experiment.defaults(dimension)
    smaller_dt = refined_experiment(experiment, "dt")
    assert smaller_dt.dt == experiment.dt/2
    assert smaller_dt.steps == experiment.steps*2
    assert smaller_dt.steps*smaller_dt.dt == experiment.steps*experiment.dt
    fine = refined_experiment(experiment, "grid")
    assert fine.dt == experiment.dt and fine.steps == experiment.steps
    assert fine.configuration().initial_values.dx == pytest.approx(experiment.configuration().initial_values.dx/2)
    if dimension == 2:
        assert fine.frames < experiment.frames
    fine.configuration()


def test_difference_uses_spatial_interpolation_and_reports_geometry_change():
    original = synthetic(Experiment(nx=48, ny=32, steps=2, px=2), value=0.01)
    fine = synthetic(refined_experiment(original.experiment, "grid"), value=0.01)
    assert density_difference(original, fine)["density_l1"] == 0
    assert density_difference(original, fine)["geometry_changed"]
    fine.densities += np.float32(0.001)
    expected = float(abs(fine.densities[0, 0, 0]-original.densities[0, 0, 0]))*48*32*original.experiment.configuration().cell_volume
    assert density_difference(original, fine)["density_l1"] == pytest.approx(expected)
    fine.summary["times"][-1] *= 2
    with pytest.raises(ValueError, match="sluttid"):
        density_difference(original, fine)


def test_complete_result_bytes_reopen_without_simulation(monkeypatch):
    run = calculate(Experiment(nx=48, ny=32, steps=2, px=2))
    buffer = io.BytesIO()
    write_result(run, buffer)
    def forbidden(*args, **kwargs):
        pytest.fail("Opening a result must not propagate")
    monkeypatch.setattr("schroedinger.app_model.simulate", forbidden)
    buffer.seek(0)
    loaded = read_result(buffer)
    np.testing.assert_array_equal(loaded.densities, run.densities)
    assert loaded.experiment == run.experiment
    assert loaded.summary == json.loads(json.dumps(run.summary))


@pytest.mark.parametrize("corrupt", ["times", "norm", "density"])
def test_result_import_rejects_inconsistent_data(corrupt):
    run = synthetic(Experiment(nx=48, ny=32, steps=2, px=2))
    if corrupt == "times":
        run.summary["times"] = [0, 0]
    elif corrupt == "norm":
        run.summary["probability"] = [5, 5]
    else:
        run.densities[0, 0, 0] = -1
    buffer = io.BytesIO()
    write_result(run, buffer)
    buffer.seek(0)
    with pytest.raises(ValueError):
        read_result(buffer)


@pytest.mark.parametrize("member", ["metadata.npy", "densities.npy"])
def test_declared_huge_numpy_arrays_rejected_before_allocation(member):
    run = synthetic(Experiment(nx=48, ny=32, steps=2, px=2))
    good = io.BytesIO()
    write_result(run, good)
    bad_header = io.BytesIO()
    np.lib.format.write_array_header_1_0(bad_header,
        {"descr": "<U999999999" if member == "metadata.npy" else "<f4", "fortran_order": False,
         "shape": () if member == "metadata.npy" else (2, 32, 999999999)})
    corrupted = io.BytesIO()
    with ZipFile(good) as source, ZipFile(corrupted, "w") as target:
        for name in source.namelist():
            target.writestr(name, bad_header.getvalue() if name == member else source.read(name))
    corrupted.seek(0)
    with pytest.raises(ValueError):
        read_result(corrupted)
