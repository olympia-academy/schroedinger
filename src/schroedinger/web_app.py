"""Streamlit presentation layer. Start with python -m schroedinger.app."""
from dataclasses import asdict
from uuid import uuid4

import numpy as np
import pandas as pd
import streamlit as st

from schroedinger.app_jobs import JobManager
from schroedinger.app_model import Experiment, boundary_details, frame_png
from schroedinger.potentials import get_barrier_mask


SCENARIOS = {
    1: {"square_wall": "Endelige barrierer", "square_well": "Potensialbrønn",
        "free": "Fri partikkel", "harmonic": "Harmonisk potensial", "power": "Potenspotensial"},
    2: {"double_slit": "Dobbeltspalte", "single_slit": "Enkeltspalte",
        "wall": "Endelig barriere", "free": "Fri partikkel", "harmonic": "Harmonisk potensial"},
}


@st.cache_resource
def jobs():
    return JobManager()


def apply_settings(experiment):
    for name, value in asdict(experiment).items():
        st.session_state[name] = value


def change_dimension():
    apply_settings(Experiment.defaults(st.session_state.dimension))


def number(label, key, **kwargs):
    return st.number_input(label, key=key, **kwargs)


def controls():
    with st.sidebar:
        st.title("Forsøksoppsett")
        with st.expander("Åpne lagret oppsett"):
            uploaded = st.file_uploader("JSON fra en tidligere kjøring", type=["json"])
            if st.button("Bruk oppsett", disabled=uploaded is None):
                try:
                    if uploaded.size > 1024*1024:
                        raise ValueError("Oppsettfilen kan være maksimalt 1 MiB.")
                    apply_settings(Experiment.read(uploaded.getvalue().decode("utf-8")))
                    st.rerun()
                except (ValueError, UnicodeError) as exc:
                    st.error(str(exc))
        st.selectbox("Dimensjon", [2, 1], format_func=lambda value: f"{value}D",
                     key="dimension", on_change=change_dimension)
        dimension = st.session_state.dimension
        st.selectbox("Forsøk", list(SCENARIOS[dimension]), key="scenario",
                     format_func=lambda value: SCENARIOS[dimension][value])
        with st.form("experiment_form"):
            st.text_input("Navn på kjøringen", key="run_name")
            if dimension == 2:
                st.selectbox("Initial bølge", ["plane_wave", "gaussian_packet"], key="wave",
                             format_func=lambda value: {"plane_wave": "Bølgetog", "gaussian_packet": "Gaussisk bølgepakke"}[value])
            else:
                st.selectbox("Tidsmetode", ["crank_nicolson", "rk4", "auto"], key="method")
                st.caption("Crank–Nicolson bevarer normen. RK4 krever små nok tidssteg. Begge har rom- og fasefeil.")
            with st.expander("Tid og oppløsning", expanded=True):
                number("Punkter i x", "nx", min_value=8, max_value=2048, step=8)
                if dimension == 2:
                    number("Punkter i y", "ny", min_value=8, max_value=2048, step=8)
                number("Tidssteg dt", "dt", min_value=0.00000001, format="%.8f")
                number("Antall tidssteg", "steps", min_value=1, max_value=200000, step=1)
                number("Maks lagrede bilder", "frames", min_value=2, max_value=121, step=1)
            with st.expander("Bølge og enheter"):
                for label, key in (("Masse", "mass"), ("ħ", "hbar"), ("Breddeparameter σx", "sigma_x")):
                    number(label, key, min_value=0.000001, format="%.6f")
                for label, key in (("Startposisjon x", "x0"), ("Bevegelsesmengde px", "px")):
                    number(label, key, format="%.6f")
                if dimension == 2:
                    number("Startposisjon y", "y0", format="%.6f")
                    number("Bevegelsesmengde py", "py", format="%.6f")
                    number("Breddeparameter σy", "sigma_y", min_value=0.000001)
                    number("Bølgetogets innhyllingsbredde", "envelope_width", min_value=0.000001)
                st.caption("For Gaussformen er posisjonens standardavvik σ/2.")
            with st.expander("Potensial og geometri"):
                number("Endelig potensialstyrke", "potential_strength")
                number("Barrieretykkelse", "thickness", min_value=0.000001, format="%.6f")
                number("Harmonisk frekvens ω", "omega", min_value=0.000001)
                if dimension == 2:
                    number("Barrierens x-posisjon", "barrier_x")
                    number("Nominell spaltebredde", "slit_width", min_value=0.000001, format="%.6f")
                    number("Avstand mellom spaltesentre", "slit_separation", min_value=0.000001)
                    st.caption("Spaltevegger er ugjennomtrengelige; endelig potensialstyrke gjelder ikke dem.")
                else:
                    number("Venstre grense a", "well_left")
                    number("Høyre grense b", "well_right")
                    number("Eksponent n", "power", min_value=1, max_value=12)
            with st.expander("Boks og kantabsorpsjon"):
                number("x minimum", "x_min")
                number("x maksimum", "x_max")
                if dimension == 2:
                    number("y minimum", "y_min")
                    number("y maksimum", "y_max")
                st.checkbox("Kantabsorpsjon", key="absorber")
                number("Absorberens rate", "absorber_strength", min_value=0.0)
                number("Absorberens breddeandel", "absorber_width", min_value=0.000001, max_value=0.499999)
            submitted = st.form_submit_button("Kjør simulering", type="primary", disabled=jobs().busy())
        if jobs().busy() and not st.session_state.get("pending"):
            st.info("En annen fane beregner. Én kjøring tillates om gangen.")
    values = {key: st.session_state[key] for key in asdict(Experiment())}
    try:
        experiment = Experiment(**values)
        config = experiment.configuration()
        mask = get_barrier_mask(config)
        details = boundary_details(config, mask)
    except (ValueError, TypeError, OverflowError) as exc:
        st.error(f"Kontroller oppsettet: {exc}")
        return None
    if submitted:
        try:
            st.session_state.pending = jobs().start(experiment)
            st.session_state.pending_name = st.session_state.run_name.strip() or "Forsøk"
            st.rerun()
        except (ValueError, OSError) as exc:
            st.error(str(exc))
    return experiment, config, details


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
            st.caption("Nærmeste lagrede bilde brukes; de faktiske tidene kan avvike. Rutenettendring kan også endre spaltegeometrien. Sammenlikningen gir ikke en konvergensgaranti.")


def main():
    st.set_page_config(page_title="Schrödinger-lab · Akademie Olympia", page_icon="⚛", layout="wide")
    if "dimension" not in st.session_state:
        apply_settings(Experiment())
        st.session_state.run_name = "Dobbeltspalte"
    if "history" not in st.session_state:
        st.session_state.history = []
    st.title("Schrödinger-lab")
    st.caption("Akademie Olympia · Lokal forsøksapp for fysikk, vurdering og utvikling")
    preview = controls()
    if preview:
        experiment, config, details = preview
        iv, sp = config.initial_values, config.simulation_params
        count = 1 + sp.steps//sp.save_every + int(sp.steps % sp.save_every != 0)
        cells = iv.nx*(iv.ny if config.dimension == 2 else 1)
        columns = st.columns(4)
        columns[0].metric("Planlagt sluttid", f"{sp.steps*iv.dt:.6g}")
        columns[1].metric("dx", f"{iv.dx:.6g}")
        columns[2].metric("Lagrede bilder", count)
        columns[3].metric("Tetthetsbilder", f"{cells*count*4/1024**2:.1f} MiB")
        st.caption(f"Ytterkant: {details['outer']}. Absorber: {'på' if experiment.absorber else 'av'}. Beregningen bruker en separat prosess og kan avbrytes.")
        if details.get("opening_widths"):
            st.caption("Åpninger mellom diskrete nullpunkter: " + ", ".join(f"{width:.6g}" for width in details["opening_widths"]))
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
                st.session_state.history = (st.session_state.history + [{"id": uuid4().hex, "name": st.session_state.pending_name, "run": run}])[-2:]
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
