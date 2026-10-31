"""Display encodings preserve saved densities, axes and physical diagnostics."""
import base64
from dataclasses import replace
import io

from matplotlib import colormaps
import numpy as np
from PIL import Image
import pytest

from schroedinger.app_model import Experiment, calculate
from schroedinger.app_playback import prepare_player


def test_2d_native_pixels_orientation_fixed_scale_and_physical_diagnostics(monkeypatch):
    run = calculate(Experiment(nx=48, ny=32, px=2.0, steps=3, frames=3,
                               scenario="free"))
    before = run.densities.copy()
    def forbidden(*args, **kwargs):
        pytest.fail("Preparing playback must not propagate the wave")
    monkeypatch.setattr("schroedinger.app_model.simulate", forbidden)
    payload = prepare_player(run, "sample")
    assert payload["times"] == run.times.tolist()
    assert payload["probability"] == run.summary["probability"]
    assert payload["absorbed"] == run.summary["absorbed_probability"]
    assert len(payload["images"]) == len(run.times)
    palette = colormaps["inferno"](np.linspace(0, 1, 256), bytes=True)[:, :3]
    for source, density in zip(payload["images"], run.densities):
        pixels = np.array(Image.open(io.BytesIO(base64.b64decode(source.split(",")[1]))))
        assert pixels.shape == (32, 48, 3)
        indices = np.clip(density/payload["vmax"]*255, 0, 255).astype(np.uint8)
        np.testing.assert_array_equal(pixels, np.flipud(palette[indices]))
    np.testing.assert_array_equal(run.densities, before)
    iv = run.experiment.configuration().initial_values
    assert payload["x_min"] == iv.x_min-iv.dx/2
    assert payload["y_max"] == iv.y_max-iv.dy/2


@pytest.mark.parametrize("method", ["crank_nicolson", "rk4"])
def test_1d_lossless_float32_densities_and_potential(method):
    run = calculate(replace(Experiment.defaults(1), method=method,
                            nx=96, px=2.0, dt=0.001, steps=5, frames=4))
    payload = prepare_player(run, "line")
    actual = np.frombuffer(base64.b64decode(payload["density"]), dtype="<f4")
    np.testing.assert_array_equal(actual.reshape(run.densities.shape), run.densities)
    assert payload["encoding"] == "float32-le"
    assert payload["solver"] == method
    assert len(payload["potential"]) == run.experiment.nx
    assert payload["times"] == run.times.tolist()


def test_default_stores_more_frames_within_existing_memory_cap():
    default = Experiment()
    config = default.configuration()
    steps = config.simulation_params
    count = 1+default.steps//steps.save_every+int(default.steps % steps.save_every != 0)
    assert count == 91
    assert count*default.nx*default.ny*4 < 128*1024**2
    replace(default, ny=384).configuration()
