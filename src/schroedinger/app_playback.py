"""Prepare saved frames once; play them entirely in the browser."""
import base64
from functools import lru_cache
import io
from pathlib import Path
from time import perf_counter

from matplotlib import colormaps
import numpy as np
from PIL import Image

from .potentials import get_barrier_mask, get_potential


def prepare_player(run, identifier):
    """Encode display data once. No propagation, temporal interpolation or resampling."""
    start = perf_counter()
    config = run.experiment.configuration()
    iv = config.initial_values
    payload = {
        "id": identifier, "dimension": config.dimension,
        "times": run.times.tolist(), "probability": run.summary["probability"],
        "absorbed": run.summary["absorbed_probability"],
        "solver": run.summary["solver"],
        "budget_error": run.summary["max_probability_budget_error"],
        "nx": iv.nx, "x_min": float(iv.x_grid[0]), "x_max": float(iv.x_grid[-1]),
    }
    if config.dimension == 2:
        samples = run.densities.ravel()[::max(1, run.densities.size//150000)]
        vmax = max(float(np.percentile(samples, 99.5)), float(run.densities.max())*0.01, 1e-12)
        palette = colormaps["inferno"](np.linspace(0, 1, 256), bytes=True)[:, :3]
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
            indices = np.clip(density/vmax*255, 0, 255).astype(np.uint8)
            pixels = palette[indices].copy()
            pixels[outline] = 255
            buffer = io.BytesIO()
            Image.fromarray(np.flipud(pixels)).save(buffer, format="PNG", compress_level=1)
            images.append("data:image/png;base64,"+base64.b64encode(buffer.getvalue()).decode("ascii"))
        payload.update(images=images, palette=palette.tolist(), vmax=vmax, ny=iv.ny,
                       x_min=iv.x_min-iv.dx/2, x_max=iv.x_max-iv.dx/2,
                       y_min=iv.y_min-iv.dy/2, y_max=iv.y_max-iv.dy/2)
    else:
        values = np.ascontiguousarray(run.densities, dtype="<f4")
        potential = get_potential(config)
        payload.update(density=base64.b64encode(values.tobytes()).decode("ascii"),
                       encoding="float32-le", density_max=max(float(values.max())*1.1, 1e-12),
                       potential=potential.tolist() if np.ptp(potential) else [])
    payload["preparation_seconds"] = perf_counter()-start
    return payload


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
  <div class="view">
    <canvas role="img" aria-label="Sannsynlighetstetthet"></canvas>
    <div class="metrics">
      <div>Fysisk tid<strong data-role="time"></strong></div>
      <div>Sannsynlighet i boksen<strong data-role="probability"></strong></div>
      <div>Absorbert sannsynlighet<strong data-role="absorbed"></strong></div>
      <small data-role="solver"></small><small data-role="budget"></small>
    </div>
  </div>
  <button type="button" data-action="download" disabled>Last ned bildet</button>
  <p class="note">Avspillingen bruker lagrede bilder. Hastigheten endrer visningen, ikke fysikken.</p>
</section>
"""
CSS = """
.player {font-family:var(--st-font,sans-serif);color:var(--st-text-color,#202b38)}
.toolbar {display:flex;gap:12px;align-items:end;flex-wrap:wrap}
button,select {font:inherit;border:1px solid #b5bac4;border-radius:7px;padding:9px 14px;background:var(--st-background-color,white);color:inherit;cursor:pointer}
button[data-action=play] {background:#d73848;color:white;border-color:#d73848;min-width:90px}
button:disabled,select:disabled {opacity:.45;cursor:wait}
.toolbar label {font-size:14px;display:flex;gap:10px;align-items:center}
.status,.note {font-size:13px;opacity:.75;margin:12px 0}
.seek-label {display:block;font-size:14px;margin:12px 0}
output {float:right;font-variant-numeric:tabular-nums}
input[type=range] {display:block;width:100%;margin:12px 0;accent-color:#d73848}
.view {display:grid;grid-template-columns:minmax(0,2.5fr) minmax(140px,1fr);gap:20px;align-items:start}
canvas {width:100%;height:auto;background:white;display:block}
.metrics {display:grid;gap:20px;padding-top:12px;font-size:14px}
.metrics strong {display:block;font-size:27px;font-weight:500;font-variant-numeric:tabular-nums;margin-top:6px}
.metrics small {opacity:.75;overflow-wrap:anywhere}
@media(max-width:650px) {.view{display:block}.metrics{grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.metrics strong{font-size:20px}.metrics small{grid-column:1/-1}.toolbar{gap:8px}}
"""


@lru_cache(maxsize=1)
def _component():
    import streamlit.components.v2 as components
    return components.component("saved_frame_player", html=HTML, css=CSS,
                                js=Path(__file__).with_name("player.mjs").read_text(encoding="utf-8"))


def show_player(run, identifier):
    import streamlit as st
    if st.session_state.get("player_prepared_for") != identifier:
        with st.spinner("Klargjør bilder for avspilling …"):
            st.session_state.player_payload = prepare_player(run, identifier)
        st.session_state.player_prepared_for = identifier
    # No state or trigger callbacks: buttons and animation never rerun Python.
    _component()(data=st.session_state.player_payload, key=f"browser_player_{identifier}")
