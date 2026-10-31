import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest
from schroedinger import get_wave_packet, simulate
from schroedinger.visualization import animate


@pytest.mark.parametrize("scenario", ["free", "wall", "single_slit", "double_slit"])
def test_2d_cli_exports_real_results(tmp_path, scenario):
    output = tmp_path / f"{scenario}.png"
    command = [sys.executable, "-m", "schroedinger", "--scenario", scenario,
               "--nx", "48", "--ny", "32", "--px", "2", "--steps", "3",
               "--save-every", "2", "--headless", "--no-progress", "--output", str(output)]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=45)
    assert completed.returncode == 0, completed.stderr
    assert output.stat().st_size > 1000
    data = json.loads(output.with_suffix(".json").read_text())
    assert data["frames"] == 3
    assert data["max_probability_budget_error"] < 1e-10
    assert "density" in data["frame_storage"]


def test_1d_legacy_entry_point_and_bad_cli_arguments(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "one.png"
    completed = subprocess.run(
        [sys.executable, "main.py", "--nx", "96", "--px", "2", "--steps", "3",
         "--headless", "--no-progress", "--output", str(output)],
        cwd=root / "1d", capture_output=True, text=True, timeout=45)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(output.with_suffix(".json").read_text())["solver"] == "crank_nicolson"
    invalid = subprocess.run(
        [sys.executable, "-m", "schroedinger", "--nx", "2"],
        capture_output=True, text=True, timeout=15)
    assert invalid.returncode == 2
    assert "Nyquist" in invalid.stderr


@pytest.mark.parametrize("dimension,solver", [(1, "crank_nicolson"), (2, "dirichlet_sine_strang")])
def test_imported_legacy_main_keeps_its_dimension_and_handles_zero_steps(tmp_path, dimension, solver):
    import importlib.util
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(f"legacy_main_{dimension}", root / f"{dimension}d" / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.main(["--nx", "96", "--px", "2", "--steps", "0", "--headless",
                          "--no-progress", "--output", str(tmp_path / f"{dimension}.png")])
    assert result.solver == solver
    assert len(result) == 1
    assert result.times[0] == 0


def test_animation_scrubbing_preserves_saved_frames(config2):
    import matplotlib.pyplot as plt
    config2.simulation_params.steps = 3
    config2.simulation_params.save_every = 1
    result = simulate(get_wave_packet(config2), 0, config2)
    saved = result[-1].copy()
    anim = animate(result, config2, show=False)
    anim._fig.canvas.draw()
    pause, restart, slider = anim._schroedinger_controls
    slider.set_val(2)
    assert pause.label.get_text() == "Play"
    assert f"t = {result.times[2]:.3f}" in anim._fig.axes[0].get_title()
    assert np.array_equal(saved, result[-1])
    restart._observers.process("clicked", None)
    assert pause.label.get_text() == "Pause"
    plt.close(anim._fig)
