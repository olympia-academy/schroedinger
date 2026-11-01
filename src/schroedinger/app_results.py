"""Result viewing, portable files and explicit numerical checks."""
import io
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd
import streamlit as st

from .app_analysis import density_difference, refined_experiment
from .app_model import read_result, write_result
from .app_playback import show_player
from .app_presets import changes
from .app_wavepacket import show_free_packet


def add_entry(run, name, base_id=None, validation=None):
    entry = {"id": uuid4().hex, "name": name, "run": run, "validation": validation}
    base = next((item for item in st.session_state.history if item["id"] == base_id), None)
    st.session_state.history = [base, entry] if base else (st.session_state.history+[entry])[-2:]
    st.session_state.selected_run = entry["id"]
    return entry


def import_results():
    with st.sidebar.expander("Åpne komplett resultat"):
        uploaded = st.file_uploader("Resultatfil (.npz)", type=["npz"], key="result_file")
        st.caption("Åpner lagrede tetthetsbilder, oppsett og diagnostikk uten ny beregning. De to siste resultatene beholdes i minnet.")
        if st.button("Åpne resultat", disabled=uploaded is None):
            try:
                if uploaded.size > 160*1024**2:
                    raise ValueError("Resultatfilen må være mindre enn 160 MiB.")
                uploaded.seek(0)
                run = read_result(uploaded)
                add_entry(run, f"Åpnet: {Path(uploaded.name).stem}")
                st.rerun()
            except (ValueError, OSError) as exc:
                st.error(f"Kunne ikke åpne resultatet: {exc}")


def budget_chart(run):
    return pd.DataFrame({"P i boksen": run.summary["probability"],
                         "Absorbert": run.summary["absorbed_probability"]},
                        index=pd.Index(run.times, name="Fysisk tid"))


def numerical_check(entry, jobs):
    with st.expander("Kontroller numerisk nøyaktighet"):
        st.write("Sammenlikn den valgte kjøringen med halvert tidssteg eller finere rutenett. Fysisk sluttid beholdes.")
        kind = st.selectbox("Kontroll", ["dt", "grid"],
                            format_func=lambda value: {"dt": "Halvert tidssteg", "grid": "Dobbelt så fint rutenett"}[value], key="refinement_kind")
        try:
            refined = refined_experiment(entry["run"].experiment, kind)
            st.caption(f"Ny kjøring: nx={refined.nx}"+(f", ny={refined.ny}" if refined.dimension == 2 else "")+
                       f", dt={refined.dt:g}, {refined.steps} beregningssteg, maks {refined.frames} lagrede bilder.")
            if refined.frames < entry["run"].experiment.frames:
                st.caption("Antall lagrede bilder reduseres for å holde minnegrensen. Alle beregningssteg gjennomføres.")
            if kind == "grid":
                st.caption("Et nytt rutenett kan flytte diskrete spaltekanter og nullpunkter. Geometriforskjellen rapporteres sammen med resultatet.")
            if st.button("Kjør kontroll", key="run_refinement", disabled=jobs.busy()):
                st.session_state.pending = jobs.start(refined)
                st.session_state.pending_name = "Kontroll: "+("halvert dt" if kind == "dt" else "finere rutenett")
                st.session_state.pending_base = entry["id"]
                st.session_state.pending_validation = {"kind": kind, "base": entry["id"]}
                st.rerun()
        except (ValueError, OSError) as exc:
            st.info(f"Denne kontrollen kan ikke kjøres med oppsettet: {exc}")
        for item in st.session_state.history:
            validation = item.get("validation")
            base = next((base for base in st.session_state.history
                         if validation and base["id"] == validation["base"]), None)
            if base:
                difference = density_difference(base["run"], item["run"])
                st.write(f"Tetthetsforskjell ved sluttid, ∫|ρ₁−ρ₂| dV: {difference['density_l1']:.6g}. "
                         f"Forskjell i P i boksen: {difference['probability_difference']:.3g}.")
                if difference["geometry_changed"]:
                    st.warning("Diskrete randkoordinater/geometri er endret. Avviket blander rutenettfeil med endret representert geometri.")
                st.caption("Tetthet fra kontrollen interpoleres i rom til utgangsrutenettet ved behov. Ingen tidsinterpolasjon. Dette målet tester ikke bølgefunksjonens fase.")
        st.caption("Én sammenlikning dokumenterer et avvik, ikke konvergens. Gjenta kontrollen ved behov. Normbevaring alene viser ikke nøyaktighet.")


def show_results(jobs):
    history = st.session_state.history
    if not history:
        st.info("Velg et forsøk i sidepanelet og trykk Kjør simulering. Ingen beregning starter automatisk.")
        return
    entries = {entry["id"]: entry for entry in history}
    if st.session_state.get("selected_run") not in entries:
        st.session_state.pop("selected_run", None)
    selected = st.selectbox("Vis kjøring", list(entries), index=len(entries)-1,
                            format_func=lambda key: entries[key]["name"], key="selected_run")
    entry, run = entries[selected], entries[selected]["run"]
    same_dimension = len(history) == 2 and history[0]["run"].experiment.dimension == history[1]["run"].experiment.dimension
    together = st.toggle("Spill av begge sammen", value=True, key="sync_compare") if same_dimension else False
    displayed = history if together else [entry]
    palette, gamma, screen_x = "YlGnBu", 0.5, None
    with st.expander("Visning og målinger"):
        if run.experiment.dimension == 2:
            color = st.radio("Fargeskala", ["Lys", "Mørk"], horizontal=True, key="display_colors")
            palette = "YlGnBu" if color == "Lys" else "inferno"
            gamma = 0.5 if st.checkbox("Fremhev svake mønstre", value=True, key="display_emphasis") else 1.0
            configs = [item["run"].experiment.configuration() for item in displayed]
            lo = max(float(config.initial_values.x_grid[0]) for config in configs)
            hi = min(float(config.initial_values.x_grid[-1]) for config in configs)
            if lo < hi:
                initial = float(np.clip(run.experiment.barrier_x+0.25*(hi-run.experiment.barrier_x), lo, hi))
                if not lo <= st.session_state.get("profile_x", initial) <= hi:
                    st.session_state.pop("profile_x", None)
                screen_x = st.number_input("Profilens x-posisjon", min_value=lo, max_value=hi,
                                           value=initial, key="profile_x", format="%.4f")
            st.caption("Fargeskalaen er fast gjennom tiden og felles ved sammenlikning. Gamma fremhever lave tettheter; fargelinjen viser faktiske tetthetsverdier. De høyeste verdiene kan være mettede.")
        st.caption("Regionandelene viser sannsynlighet til venstre for, i og til høyre for barrieren. Venstre/høyre andel inkluderer også en eventuell innkommende bølge og påvirkes av absorpsjon og tilbakekomst. De er ikke automatisk refleksjons-/transmisjonskoeffisienter.")
        st.caption("x, tid og potensial bruker modellens valgte enheter. Profilen viser øyeblikkelig tetthet, ikke akkumulert strøm eller detektortreff.")
    show_player(displayed, palette, gamma, screen_x)
    st.line_chart(budget_chart(run))
    show_free_packet(run, entry["name"], selected)
    with st.expander("Lagre resultat og oppsett"):
        st.caption("Komplett resultatfil inneholder alle lagrede float32-tettheter, tider, oppsett og diagnostikk. Fase er ikke lagret. JSON inneholder bare oppsett og rapport.")
        if st.button("Klargjør komplett resultatfil", key="prepare_export"):
            with st.spinner("Komprimerer resultat …"):
                buffer = io.BytesIO()
                write_result(run, buffer)
                st.session_state.result_export = (selected, buffer.getvalue())
        exported = st.session_state.get("result_export")
        if exported and exported[0] == selected:
            st.download_button("Last ned komplett resultat", exported[1], "schroedinger-resultat.npz", "application/octet-stream", key="download_result")
        st.download_button("Last ned oppsett og rapport", run.configuration_json(), "experiment.json", "application/json")
        st.download_button("Last ned sannsynlighetsregnskap", budget_chart(run).to_csv(), "probability.csv", "text/csv")
    with st.expander("Oppsett og diskrete randkoordinater"):
        st.json(run.metadata())
    numerical_check(entry, jobs)
    st.caption("De to siste resultatene beholdes i denne nettleserøkten. Last ned komplette resultatfiler for å beholde dem etter omstart.")
    if len(history) == 2:
        with st.expander("Forskjeller mellom kjøringene", expanded=True):
            rows = []
            for item in history:
                experiment, summary = item["run"].experiment, item["run"].summary
                rows.append({"Kjøring": item["name"], "Rutenett": f"{experiment.nx} × {experiment.ny}" if experiment.dimension == 2 else str(experiment.nx),
                             "dt": experiment.dt, "Sluttid": float(item["run"].times[-1]),
                             "Ytterkant": summary["boundaries"]["outer"],
                             "Spalteåpninger mellom nullpunkter": str(summary["boundaries"].get("opening_widths", []))})
            st.dataframe(rows, hide_index=True)
            differences = changes(history[0]["run"].experiment, history[1]["run"].experiment)
            if differences:
                st.write("Dette er endret mellom kjøringene:")
                st.dataframe(differences, hide_index=True)
            if together:
                st.caption("Felles tidsvelger velger nærmeste faktisk lagrede bilde i hver kjøring. Hver visning oppgir sin faktiske tid og avvik fra ønsket tid. Fargeskalaen og profilens høydeakse er felles.")
