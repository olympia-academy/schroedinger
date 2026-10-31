from dataclasses import replace

import pytest

from schroedinger.app_model import boundary_details
from schroedinger.app_presets import PRESETS, at_final_time, changes, comparison_parameters, preset
from schroedinger import get_barrier_mask


@pytest.mark.parametrize("name", list(PRESETS))
def test_presets_are_valid_and_keep_their_default_time(name):
    experiment = preset(name)
    actual = at_final_time(experiment, experiment.dt*experiment.steps)
    actual.configuration()
    assert actual == experiment


def test_requested_time_is_reached_without_exceeding_requested_dt():
    original = replace(preset("double_slit"), dt=0.03)
    actual = at_final_time(original, 0.1)
    assert actual.steps == 4
    assert actual.dt == 0.025
    assert actual.dt*actual.steps == pytest.approx(0.1)
    assert original.dt == 0.03


@pytest.mark.parametrize("time", [0, -1, float("nan"), float("inf"), 1e100])
def test_invalid_or_excessive_times_are_rejected(time):
    with pytest.raises(ValueError):
        at_final_time(preset("double_slit"), time)


def test_one_grid_change_keeps_time_and_exposes_geometry_change():
    original = preset("double_slit")
    edited = at_final_time(replace(original, ny=384), original.steps*original.dt)
    assert [row["Parameter"] for row in changes(original, edited)] == ["ny"]
    first, second = original.configuration(), edited.configuration()
    assert boundary_details(first, get_barrier_mask(first))["opening_widths"] == pytest.approx([0.703125]*2)
    assert boundary_details(second, get_barrier_mask(second))["opening_widths"] == pytest.approx([0.625]*2)


def test_controlled_choices_are_relevant_and_1d_methods_remain_available():
    assert "slit_width" not in comparison_parameters(preset("free"))
    assert "slit_width" in comparison_parameters(preset("double_slit"))
    assert "method" in comparison_parameters(preset("tunneling"))
