"""Streamlit presentation layer. Start with python -m schroedinger.app."""
from uuid import uuid4

import numpy as np
import pandas as pd
import streamlit as st

from schroedinger.app_jobs import JobManager
from schroedinger.app_model import frame_png
from schroedinger.app_controls import initialize, controls
from schroedinger.app_presets import changes


@st.cache_resource
def jobs():
    return JobManager()


def budget_chart(run):
    return pd.DataFrame({"P i boksen": run.summary["probability"],
                         "Absorbert": run.summary["absorbed_probability"]},
                        index=pd.Index(run.times, name="Fysisk tid"))


def show_results():
    history = st.session_state.history
    if not history:
        st.info("Velg et forsøk i sidepanelet og trykk Kjør simulering. Ingen beregning starter automatisk.")
        return
    entries = {entry["id"]: entry for entry in history}
    if st.session_state.get("selected_run") not in entries:
        st.session_state.pop("selected_run", None)
    selected = st.selectbox("Vis kjøring", list(entries), index=len(entries)-1,
                            format_func=lambda key: entries[key]["name"], key="selected_run")
    run = entries[selected]["run"]
    frame = st.slider("Lagret tidssteg", 0, len(run.times)-1, len(run.times)-1, key=f"frame_{selected}")
    left, right = st.columns([2, 1])
    with left:
        image = frame_png(run, frame)
        st.image(image, width="stretch")
    with right:
        st.metric("Fysisk tid", f"{run.times[frame]:.6g}")
        st.metric("Sannsynlighet i boksen", f"{run.summary['probability'][frame]:.6f}")
        st.metric("Absorbert sannsynlighet", f"{run.summary['absorbed_probability'][frame]:.6f}")
        st.caption(f"Metode: {run.summary['solver']}")
        st.caption(f"Maks regnskapsavvik: {run.summary['max_probability_budget_error']:.2e}")
    st.line_chart(budget_chart(run))
    with st.expander("Oppsett og diskrete randkoordinater"):
        st.json(run.metadata())
    a, b, c = st.columns(3)
    a.download_button("Last ned oppsett og rapport", run.configuration_json(), "experiment.json", "application/json")
    b.download_button("Last ned bildet", image, "snapshot.png", "image/png")
    c.download_button("Last ned sannsynlighetsregnskap", budget_chart(run).to_csv(), "probability.csv", "text/csv")
    st.caption("Appen lagrer tetthet, ikke bølgefunksjonens fase. Bruk Python-API-et for faseanalyse. De to siste kjøringene beholdes i denne nettleserøkten.")
    if len(history) == 2:
        with st.expander("Sammenlikn de to siste kjøringene", expanded=True):
            first, second = (entry["run"] for entry in history)
            if first.experiment.dimension != second.experiment.dimension:
                st.info("Velg samme dimensjon i begge kjøringer for en sammenlikning.")
                return
            end = min(first.times[-1], second.times[-1])
            if st.session_state.get("comparison_time", 0) > end:
                st.session_state.pop("comparison_time", None)
            target = st.slider("Felles ønsket tidspunkt", 0.0, float(end), float(end), key="comparison_time")
            vmax = None
            frames = [int(np.argmin(abs(item.times-target))) for item in (first, second)]
            if first.experiment.dimension == 2:
                vmax = max(float(np.max(item.densities[frame])) for item, frame in zip((first, second), frames))
            for column, entry, index in zip(st.columns(2), history, frames):
                with column:
                    item = entry["run"]
                    st.write(entry["name"])
                    st.image(frame_png(item, index, vmax=vmax), width="stretch")
                    st.caption(f"Faktisk lagret tid: {item.times[index]:.6g}; dt={item.experiment.dt:g}")
            rows = []
            for entry in history:
                item = entry["run"]
                rows.append({"Kjøring": entry["name"], "Rutenett": f"{item.experiment.nx} x {item.experiment.ny}" if item.experiment.dimension == 2 else str(item.experiment.nx),
                             "dt": item.experiment.dt, "Sluttid": float(item.times[-1]),
                             "Ytterkant": item.summary["boundaries"]["outer"],
                             "Spalteåpninger mellom nullpunkter": str(item.summary["boundaries"].get("opening_widths", []))})
            st.dataframe(rows, hide_index=True)
            differences = changes(first.experiment, second.experiment)
            if differences:
                st.write("Dette er endret mellom kjøringene:")
                labels = {"slit_width": "Spaltebredde", "slit_separation": "Spalteavstand",
                          "dt": "Faktisk tidssteg", "steps": "Antall beregningssteg",
                          "nx": "Punkter i x", "ny": "Punkter i y", "method": "Tidsmetode",
                          "px": "Bevegelsesmengde", "potential_strength": "Potensialstyrke"}
                st.dataframe([{**row, "Parameter": labels.get(row["Parameter"], row["Parameter"])}
                              for row in differences], hide_index=True)
                st.caption("dt og antall steg kan følge med automatisk for å holde fysisk sluttid fast.")
            st.caption("Nærmeste lagrede bilde brukes; de faktiske tidene kan avvike. Rutenettendring kan også endre spaltegeometrien. Sammenlikningen gir ikke en konvergensgaranti.")


def main():
    st.set_page_config(page_title="Schrödinger-lab · Akademie Olympia", page_icon="⚛", layout="wide")
    initialize()
    if "history" not in st.session_state:
        st.session_state.history = []
    st.title("Schrödinger-lab")
    st.caption("Akademie Olympia · Utforsk et forsøk eller sammenlikn én endring")
    preview = controls(jobs())
    if preview:
        experiment, config, details = preview
        iv, sp = config.initial_values, config.simulation_params
        st.caption(f"Fysisk sluttid: {sp.steps*iv.dt:.6g}. Trykk Kjør simulering når du er klar.")
        with st.expander("Beregningsdetaljer", expanded=st.session_state.work_mode == "Avansert"):
            count = 1 + sp.steps//sp.save_every + int(sp.steps % sp.save_every != 0)
            cells = iv.nx*(iv.ny if config.dimension == 2 else 1)
            st.write(f"{sp.steps} steg · faktisk dt={iv.dt:.10g} · dx={iv.dx:.6g}")
            st.write(f"{count} lagrede bilder · {cells*count*4/1024**2:.1f} MiB tetthetsbilder")
            st.write(f"Ytterkant: {details['outer']}. Absorber: {'på' if experiment.absorber else 'av'}.")
            if details.get("opening_widths"):
                st.write("Åpninger mellom diskrete nullpunkter: " + ", ".join(f"{width:.6g}" for width in details["opening_widths"]))
            st.caption("Ferdige oppsett er utgangspunkt for utforskning. De er ikke konvergensgarantier.")
    if st.session_state.get("flash"):
        st.info(st.session_state.pop("flash"))

    @st.fragment(run_every=1.0 if st.session_state.get("pending") else None)
    def monitor():
        identifier = st.session_state.get("pending")
        if not identifier:
            return
        status = jobs().status(identifier)
        if status["status"] == "running":
            st.info(f"Beregner · {status['seconds']:.0f} sekunder")
            if st.button("Avbryt beregningen", key="cancel_job"):
                jobs().cancel(identifier)
                st.session_state.pending = None
                st.session_state.flash = "Beregningen ble avbrutt. Tidligere resultater er beholdt."
                st.rerun()
        else:
            if status["status"] == "complete":
                run = jobs().collect(identifier)
                entry = {"id": uuid4().hex, "name": st.session_state.pending_name, "run": run}
                base = next((item for item in st.session_state.history
                             if item["id"] == st.session_state.get("pending_base")), None)
                st.session_state.history = [base, entry] if base else (st.session_state.history + [entry])[-2:]
            else:
                st.session_state.flash = status.get("message", "Beregningen mislyktes.")
                jobs().cancel(identifier)
            st.session_state.pending = None
            st.rerun()

    monitor()
    show_results()
    with st.expander("Fysikk og tolkning"):
        st.markdown("""**Periodiske ytterkanter** kan sende bølger inn igjen på motsatt side.
**Dirichlet-ytterkanter** reflekterer bølger når absorberen er av.
Absorberen demper bølger før kanten, men er ikke en eksakt åpen grense.
Å slå den av endrer ikke randtypen. Spalteveggen og ytterkantene er ulike grenser.

Normbevaring dokumenterer sannsynlighetsregnskapet. Nøyaktige interferensmønstre
krever egne kontroller av tidssteg, rutenett, geometri og boksstørrelse.
Sammenlikn ved samme fysiske tid. Standardinnstillingene er demonstrasjoner.""")


main()
