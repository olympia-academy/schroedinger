"""Streamlit presentation layer. Start with python -m schroedinger.app."""
import streamlit as st

from schroedinger.app_jobs import JobManager
from schroedinger.app_controls import initialize, controls
from schroedinger.app_results import show_results, import_results, add_entry


@st.cache_resource
def jobs():
    return JobManager()


def main():
    st.set_page_config(page_title="Schrödinger-lab · Akademie Olympia", page_icon="⚛", layout="wide")
    initialize()
    if "history" not in st.session_state:
        st.session_state.history = []
    st.title("Schrödinger-lab")
    st.caption("Akademie Olympia · Utforsk et forsøk eller sammenlikn én endring")
    import_results()
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
                add_entry(run, st.session_state.pending_name,
                          st.session_state.get("pending_base"),
                          st.session_state.pop("pending_validation", None))
            else:
                st.session_state.flash = status.get("message", "Beregningen mislyktes.")
                jobs().cancel(identifier)
            st.session_state.pending = None
            st.rerun()

    monitor()
    show_results(jobs())
    with st.expander("Fysikk og tolkning"):
        st.markdown("""**Periodiske ytterkanter** kan sende bølger inn igjen på motsatt side.
**Dirichlet-ytterkanter** reflekterer bølger når absorberen er av.
Absorberen demper bølger før kanten, men er ikke en eksakt åpen grense.
Å slå den av endrer ikke randtypen. Spalteveggen og ytterkantene er ulike grenser.

Normbevaring dokumenterer sannsynlighetsregnskapet. Nøyaktige interferensmønstre
krever egne kontroller av tidssteg, rutenett, geometri og boksstørrelse.
Sammenlikn ved samme fysiske tid. Standardinnstillingene er demonstrasjoner.""")


main()
