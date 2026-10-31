import pytest

from schroedinger.app_playback import advance


def test_playback_clock_retains_remainder_and_clamps_at_the_end():
    frame, updated, playing = advance(0, 10, 10.6, 4, 10)
    assert (frame, updated, playing) == (2, 10.5, True)
    assert advance(frame, updated, 10.76, 4, 10) == (3, 10.75, True)
    assert advance(3, 10.75, 100, 4, 10)[::2] == (9, False)
    assert advance(0, 10, 9, 4, 10) == (0, 10, True)


@pytest.mark.parametrize("fps", [0, -1, float("nan"), float("inf")])
def test_invalid_playback_rates_are_rejected(fps):
    with pytest.raises(ValueError):
        advance(0, 0, 1, fps, 10)
