"""Prepare display data once; all playback stays in the browser."""
import base64
from functools import lru_cache
import io
from pathlib import Path

from matplotlib import colormaps
import numpy as np
from PIL import Image

from .app_analysis import measurements, nearest_indices
from .potentials import get_barrier_mask, get_potential


def display_scale(runs):
    """One fixed density scale across every selected run and every saved time."""
    samples = [run.densities.ravel()[::max(1, run.densities.size//150000)] for run in runs]
    return max(float(np.percentile(values, 99.5)) for values in samples) if samples else 1.0


def prepare_player(run, identifier, *, vmax=None, palette="YlGnBu", gamma=0.5, screen_x=None):
    config = run.experiment.configuration()
    iv = config.initial_values
    payload = {
        "id": identifier, "dimension": config.dimension,
        "times": run.times.tolist(), "probability": run.summary["probability"],
        "absorbed": run.summary["absorbed_probability"],
        "solver": run.summary["solver"],
        "budget_error": run.summary["max_probability_budget_error"],
        "nx": iv.nx, "x_min": float(iv.x_grid[0]), "x_max": float(iv.x_grid[-1]),
        "measurements": measurements(run, screen_x),
    }
    if config.dimension == 2:
        if palette not in {"YlGnBu", "inferno"} or gamma not in {0.5, 1.0}:
            raise ValueError("Ukjent fargevalg.")
        vmax = max(float(vmax if vmax is not None else display_scale([run])),
                   float(run.densities.max())*0.01 if vmax is None else 0, 1e-12)
        colors = colormaps[palette](np.linspace(0, 1, 256), bytes=True)[:, :3]
        mask = get_barrier_mask(config)
        potential = get_potential(config)
        shape = mask
        if shape is None and np.ptp(potential):
            shape = potential >= (potential.min()+potential.max())/2
        outline = np.zeros(run.densities.shape[1:], dtype=bool)
        if shape is not None:
            outline[1:, :] |= shape[1:, :] != shape[:-1, :]
            outline[:, 1:] |= shape[:, 1:] != shape[:, :-1]
        images = []
        for density in run.densities:
            indices = (np.clip(density/vmax, 0, 1)**gamma*255).astype(np.uint8)
            pixels = colors[indices].copy()
            pixels[outline] = 255 if palette == "inferno" else 90
            buffer = io.BytesIO()
            Image.fromarray(np.flipud(pixels)).save(buffer, format="PNG", compress_level=1)
            images.append("data:image/png;base64,"+base64.b64encode(buffer.getvalue()).decode("ascii"))
        payload.update(images=images, palette=colors.tolist(), vmax=vmax, gamma=gamma, ny=iv.ny,
                       x_min=iv.x_min-iv.dx/2, x_max=iv.x_max-iv.dx/2,
                       y_min=iv.y_min-iv.dy/2, y_max=iv.y_max-iv.dy/2,
                       clipped_fraction=float(np.count_nonzero(run.densities > vmax)/run.densities.size))
    else:
        values = np.ascontiguousarray(run.densities, dtype="<f4")
        potential = get_potential(config)
        payload.update(density=base64.b64encode(values.tobytes()).decode("ascii"),
                       density_max=max(float(values.max())*1.1, 1e-12), encoding="float32-le",
                       potential=potential.tolist() if np.ptp(potential) else [])
    return payload


def prepare_group(entries, palette="YlGnBu", gamma=0.5, screen_x=None):
    runs = [entry["run"] for entry in entries]
    vmax = max(display_scale(runs), max(float(run.densities.max()) for run in runs)*0.01, 1e-12)
    end = min(run.times[-1] for run in runs)
    times = (np.linspace(0, end, max(len(run.times) for run in runs))
             if len(runs) > 1 else runs[0].times)
    prepared = []
    density_max = profile_max = 1e-12
    for entry in entries:
        item = prepare_player(entry["run"], entry["id"], vmax=vmax,
                              palette=palette, gamma=gamma, screen_x=screen_x)
        item["name"] = entry["name"]
        item["indices"] = nearest_indices(item["times"], times).tolist()
        density_max = max(density_max, item.get("density_max", 0))
        if "profile" in item["measurements"]:
            profile_max = max(profile_max, float(np.max(item["measurements"]["profile"]))*1.05)
        prepared.append(item)
    for item in prepared:
        item.update(density_max=density_max, profile_max=profile_max)
    return {"id": "_".join(entry["id"] for entry in entries), "times": times.tolist(), "runs": prepared}


HTML = """
<section class="player" aria-label="Avspiller for lagrede simuleringsbilder">
  <div class="toolbar">
    <button type="button" data-action="play" disabled>Spill av</button>
    <button type="button" data-action="restart" disabled>Start på nytt</button>
    <label>Hastighet <select aria-label="Avspillingshastighet" disabled>
      <option value="2">2 bilder/s</option><option value="4">4 bilder/s</option>
      <option value="8">8 bilder/s</option><option value="12" selected>12 bilder/s</option>
      <option value="24">24 bilder/s</option>
    </select></label>
  </div>
  <p class="status" role="status">Klargjør avspilling …</p>
  <label class="seek-label">Lagret tidssteg <output data-role="frame-label"></output>
    <input type="range" aria-label="Lagret tidssteg" min="0" step="1" disabled />
  </label>
  <p class="requested-time"></p>
  <div class="panels"></div>
  <button type="button" data-action="download" disabled>Last ned bildet</button>
  <p class="note">Avspillingshastigheten endrer visningen. Tettheter og sannsynligheter er uendret.</p>
  <template>
    <article class="panel">
      <h3></h3><canvas class="density" role="img" aria-label="Sannsynlighetstetthet"></canvas>
      <div class="metrics">
        <div>Faktisk fysisk tid<strong data-role="time"></strong></div>
        <div>P i boksen<strong data-role="probability"></strong></div>
        <div>Absorbert P<strong data-role="absorbed"></strong></div>
      </div>
      <p class="time-offset"></p><p class="scale"></p>
      <p class="regions"></p>
      <canvas class="profile" role="img" aria-label="Øyeblikksprofil"></canvas>
      <p class="profile-note"></p><small class="solver"></small>
    </article>
  </template>
</section>
"""
CSS = """
.player {font-family:var(--st-font,sans-serif);color:var(--st-text-color,#202b38)}
.toolbar {display:flex;gap:12px;align-items:center;flex-wrap:wrap}
button,select {font:inherit;border:1px solid #b5bac4;border-radius:7px;padding:9px 14px;background:var(--st-background-color,white);color:inherit;cursor:pointer}
button[data-action=play] {background:#d73848;color:white;border-color:#d73848;min-width:90px}
button:disabled,select:disabled {opacity:.45;cursor:wait}
.toolbar label {font-size:14px;display:flex;gap:10px;align-items:center}
.status,.note,.requested-time,.scale,.time-offset,.regions,.profile-note {font-size:13px;line-height:1.5;margin:10px 0}
.status,.note,.solver {opacity:.75}
.seek-label {display:block;font-size:14px;margin:12px 0}
output {float:right;font-variant-numeric:tabular-nums}
input[type=range] {display:block;width:100%;margin:12px 0;accent-color:#d73848}
.panels {display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,350px),1fr));gap:24px}
.panel {min-width:0} h3 {font-size:16px;margin:8px 0}
canvas {width:100%;height:auto;background:white;display:block}
.metrics {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;font-size:13px;margin-top:8px}
.metrics strong {display:block;font-size:22px;font-weight:500;font-variant-numeric:tabular-nums;margin-top:5px}
.regions {background:var(--st-secondary-background-color,#f1f4f7);padding:8px;border-radius:6px}
@media(max-width:650px) {.metrics strong{font-size:18px}.toolbar{gap:8px}}
"""


@lru_cache(maxsize=1)
def _component():
    import streamlit.components.v2 as components
    return components.component("saved_frame_player", html=HTML, css=CSS,
                                js=Path(__file__).with_name("player.mjs").read_text(encoding="utf-8"))


def show_player(entries, palette="YlGnBu", gamma=0.5, screen_x=None):
    import streamlit as st
    signature = (tuple(entry["id"] for entry in entries), palette, gamma, screen_x)
    if st.session_state.get("player_prepared_for") != signature:
        with st.spinner("Klargjør bilder for avspilling …"):
            st.session_state.player_payload = prepare_group(entries, palette, gamma, screen_x)
        st.session_state.player_prepared_for = signature
    payload = st.session_state.player_payload
    _component()(data=payload, key=f"browser_player_{payload['id']}")
