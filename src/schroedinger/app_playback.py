"""Playback of saved density frames, independent of simulation workers."""
import math
from time import monotonic

from .app_model import frame_png


def advance(frame, updated_at, now, fps, frame_count):
    """Advance by elapsed wall-clock time, clamp at the end, retain remainder."""
    if frame_count < 1 or not 0 <= frame < frame_count:
        raise ValueError("Invalid playback frame")
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("Playback rate must be positive")
    elapsed = max(0.0, now-updated_at)
    steps = int(elapsed*fps + 1e-9)
    current = min(frame+steps, frame_count-1)
    return current, updated_at+steps/fps, current < frame_count-1


def show_player(run, identifier):
    # Import only when displaying the optional app; clock tests need no Streamlit.
    import streamlit as st

    frame_key = f"frame_{identifier}"
    if st.session_state.get("playback_run") != identifier:
        st.session_state.playback_run = identifier
        st.session_state.playback_playing = False
        st.session_state.playback_updated = monotonic()
        st.session_state.playback_images = {}
    st.session_state.setdefault(frame_key, len(run.times)-1)
    st.session_state.setdefault("playback_fps", 4)

    first, second, third = st.columns([1, 1, 1.4])
    with first:
        label = "Pause" if st.session_state.playback_playing else "Spill av"
        if st.button(label, key="playback_toggle", type="primary"):
            playing = not st.session_state.playback_playing
            if playing and st.session_state[frame_key] == len(run.times)-1:
                st.session_state[frame_key] = 0
            st.session_state.playback_playing = playing
            st.session_state.playback_updated = monotonic()
            st.rerun()
    with second:
        if st.button("Start på nytt", key="playback_restart"):
            st.session_state[frame_key] = 0
            st.session_state.playback_playing = True
            st.session_state.playback_updated = monotonic()
            st.rerun()
    with third:
        def speed_changed():
            st.session_state.playback_updated = monotonic()
        st.selectbox("Hastighet", [2, 4, 8], key="playback_fps",
                     format_func=lambda fps: f"{fps} bilder/s", on_change=speed_changed)

    st.caption("Avspillingen bruker lagrede bilder. Hastigheten endrer bare visningen, ikke fysikken.")
    scheduled = st.session_state.playback_playing

    def seek():
        st.session_state.playback_playing = False
        st.session_state.playback_updated = monotonic()

    @st.fragment(run_every=1/st.session_state.playback_fps if scheduled else None)
    def render():
        # Seeking during a timed fragment must also switch off its timer.
        if st.session_state.playback_playing != scheduled:
            st.rerun(scope="app")
        if scheduled:
            frame, updated, playing = advance(st.session_state[frame_key],
                                               st.session_state.playback_updated,
                                               monotonic(), st.session_state.playback_fps,
                                               len(run.times))
            st.session_state[frame_key] = frame
            st.session_state.playback_updated = updated
            st.session_state.playback_playing = playing
            if not playing:
                st.rerun(scope="app")
        frame = st.slider("Lagret tidssteg", 0, len(run.times)-1, key=frame_key, on_change=seek)
        cache = st.session_state.playback_images
        if frame not in cache:
            cache[frame] = frame_png(run, frame)
        image = cache[frame]
        left, right = st.columns([2, 1])
        with left:
            st.image(image, width="stretch")
        with right:
            st.metric("Fysisk tid", f"{run.times[frame]:.6g}")
            st.metric("Sannsynlighet i boksen", f"{run.summary['probability'][frame]:.6f}")
            st.metric("Absorbert sannsynlighet", f"{run.summary['absorbed_probability'][frame]:.6f}")
            st.caption(f"Metode: {run.summary['solver']}")
            st.caption(f"Maks regnskapsavvik: {run.summary['max_probability_budget_error']:.2e}")
        st.download_button("Last ned bildet", image, "snapshot.png", "image/png", key="playback_download")

    render()
