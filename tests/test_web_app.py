"""Optional UI tests: simple controls and reproducible controlled comparisons."""
from pathlib import Path
import time

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1]/"src"/"schroedinger"/"web_app.py"


def wait_for_runs(app, count):
    deadline = time.monotonic()+25
    while len(app.session_state["history"]) < count and time.monotonic() < deadline:
        time.sleep(0.1)
        app.run(timeout=15)
        assert not app.exception
    assert len(app.session_state["history"]) == count


def start(app):
    next(button for button in app.button if button.label == "Kjør simulering").click().run(timeout=15)
    assert not app.exception


def small_run(app):
    app.radio(key="work_mode").set_value("Avansert").run()
    app.number_input(key="edit_nx").set_value(48)
    app.number_input(key="edit_ny").set_value(32)
    app.number_input(key="edit_px").set_value(2.0)
    app.number_input(key="edit_frames").set_value(3)
    app.number_input(key="edit_final_time").set_value(0.1171875)
    start(app)
    wait_for_runs(app, 1)


def test_simple_page_presets_and_advanced_settings_are_preserved():
    app = AppTest.from_file(str(APP)).run(timeout=15)
    assert not app.exception
    assert app.session_state["history"] == []
    assert len(app.number_input) == 3
    assert {item.key for item in app.number_input} == {"edit_slit_width", "edit_slit_separation", "edit_final_time"}
    app.radio(key="work_mode").set_value("Avansert").run()
    app.number_input(key="edit_mass").set_value(12.0).run()
    app.radio(key="work_mode").set_value("Utforsk").run()
    assert app.session_state["draft"]["mass"] == 12.0
    assert not app.session_state.get("pending")
    app.radio(key="work_mode").set_value("Avansert").run()
    assert app.number_input(key="edit_mass").value == 12.0
    app.selectbox(key="preset_key").set_value("tunneling").run()
    assert not app.exception
    assert app.selectbox(key="edit_method").options == ["crank_nicolson", "rk4", "auto"]
    app.selectbox(key="edit_method").set_value("rk4").run()
    assert app.session_state["history"] == []


def test_run_scrub_and_single_parameter_comparison_keep_time_and_baseline():
    app = AppTest.from_file(str(APP)).run(timeout=15)
    small_run(app)
    entry = app.session_state["history"][0]
    app.slider(key=f"frame_{entry['id']}").set_value(0).run(timeout=15)
    assert not app.exception
    assert not app.session_state.get("pending")
    app.radio(key="work_mode").set_value("Sammenlikn").run()
    app.number_input(key=f"one_{entry['id']}_slit_width").set_value(0.8).run()
    assert len(app.session_state["history"]) == 1
    assert entry["run"].experiment.slit_width == 0.6
    start(app)
    wait_for_runs(app, 2)
    first, second = app.session_state["history"]
    assert first["id"] == entry["id"]
    assert second["run"].experiment.slit_width == 0.8
    assert first["run"].times[-1] == second["run"].times[-1]
    assert app.slider(key="comparison_time").value == first["run"].times[-1]
    assert len(app.dataframe) == 2
    app.selectbox(key="comparison_base").set_value(first["id"]).run()
    app.number_input(key=f"one_{first['id']}_slit_width").set_value(1.0).run()
    previous_id = second["id"]
    start(app)
    deadline = time.monotonic()+25
    while app.session_state["history"][-1]["id"] == previous_id and time.monotonic() < deadline:
        time.sleep(0.1)
        app.run(timeout=15)
        assert not app.exception
    assert app.session_state["history"][0]["id"] == first["id"]
    assert app.session_state["history"][-1]["run"].experiment.slit_width == 1.0


def test_compare_without_a_run_and_cancel_long_worker():
    app = AppTest.from_file(str(APP)).run(timeout=15)
    app.radio(key="work_mode").set_value("Sammenlikn").run()
    assert not app.exception
    assert not any(button.label == "Kjør simulering" for button in app.button)
    app.radio(key="work_mode").set_value("Avansert").run()
    app.number_input(key="edit_final_time").set_value(3906.25)
    app.number_input(key="edit_frames").set_value(2)
    start(app)
    assert app.session_state["pending"]
    app.button(key="cancel_job").click().run(timeout=15)
    assert not app.exception
    assert not app.session_state.get("pending")
    assert app.session_state["history"] == []
