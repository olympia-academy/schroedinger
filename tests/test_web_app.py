"""Optional UI integration tests; installed by the app extra on Python 3.11+."""
from pathlib import Path
import time

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1]/"src"/"schroedinger"/"web_app.py"


def test_initial_page_and_1d_method_selection_do_not_start_calculation():
    app = AppTest.from_file(str(APP)).run(timeout=15)
    assert not app.exception
    assert app.session_state["history"] == []
    app.selectbox(key="dimension").set_value(1).run()
    assert not app.exception
    assert app.selectbox(key="method").options == ["crank_nicolson", "rk4", "auto"]
    app.selectbox(key="method").set_value("rk4").run()
    assert app.session_state["history"] == []
    assert not app.session_state.get("pending")


def test_run_and_frame_scrubbing_keep_the_completed_result():
    app = AppTest.from_file(str(APP)).run(timeout=15)
    app.number_input(key="nx").set_value(48)
    app.number_input(key="ny").set_value(32)
    app.number_input(key="px").set_value(2.0)
    app.number_input(key="steps").set_value(3)
    app.number_input(key="frames").set_value(3)
    next(button for button in app.button if button.label == "Kjør simulering").click().run(timeout=15)
    deadline = time.monotonic()+25
    while not app.session_state["history"] and time.monotonic() < deadline:
        time.sleep(0.1)
        app.run(timeout=15)
        assert not app.exception
    assert len(app.session_state["history"]) == 1
    entry = app.session_state["history"][0]
    app.slider(key=f"frame_{entry['id']}").set_value(0).run(timeout=15)
    assert not app.exception
    assert app.session_state["history"][0]["id"] == entry["id"]
    assert not app.session_state.get("pending")
    # A second run can be compared without recomputing either result.
    app.text_input(key="run_name").set_value("Sammenlikning")
    next(button for button in app.button if button.label == "Kjør simulering").click().run(timeout=15)
    deadline = time.monotonic()+25
    while len(app.session_state["history"]) < 2 and time.monotonic() < deadline:
        time.sleep(0.1)
        app.run(timeout=15)
        assert not app.exception
    assert len(app.session_state["history"]) == 2
    assert app.slider(key="comparison_time").value > 0
    assert len(app.dataframe) == 1


def test_ui_cancel_stops_a_long_worker_and_keeps_history():
    app = AppTest.from_file(str(APP)).run(timeout=15)
    app.number_input(key="steps").set_value(100000)
    app.number_input(key="frames").set_value(2)
    next(button for button in app.button if button.label == "Kjør simulering").click().run(timeout=15)
    assert app.session_state["pending"]
    app.button(key="cancel_job").click().run(timeout=15)
    assert not app.exception
    assert not app.session_state.get("pending")
    assert app.session_state["history"] == []
