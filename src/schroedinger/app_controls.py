"""Progressive experiment controls; calculations start only on explicit Run."""
from dataclasses import asdict, replace

import streamlit as st

from .app_model import Experiment, boundary_details
from .app_presets import PRESETS, at_final_time, comparison_parameters, preset
from .potentials import get_barrier_mask


SCENARIOS = {
    1: {"square_wall": "Endelige barrierer", "square_well": "Potensialbrønn",
        "free": "Fri partikkel", "harmonic": "Harmonisk potensial", "power": "Potenspotensial"},
    2: {"double_slit": "Dobbeltspalte", "single_slit": "Enkeltspalte",
        "wall": "Endelig barriere", "free": "Fri partikkel", "harmonic": "Harmonisk potensial"},
}


def set_editor(experiment, name="Eget oppsett", preset_key="custom", final_time=None):
    # Keep a canonical draft separate from widgets: Streamlit removes hidden
    # widget state when switching modes. Completed runs are never edited here.
    for key in list(st.session_state):
        if key.startswith("edit_"):
            del st.session_state[key]
    st.session_state.draft = asdict(experiment)
    st.session_state.target_time = experiment.steps*experiment.dt if final_time is None else final_time
    st.session_state.draft_name = name
    st.session_state.draft_preset = preset_key
    st.session_state.preset_key = preset_key


def initialize():
    if "draft" not in st.session_state:
        values = {key: st.session_state.get(key, value) for key, value in asdict(Experiment()).items()}
        experiment = Experiment(**values)
        default = experiment == Experiment()
        set_editor(experiment, "Dobbeltspalte (2D)" if default else "Eget oppsett",
                   "double_slit" if default else "custom")
    st.session_state.setdefault("work_mode", "Utforsk")
    st.session_state.setdefault("draft_preset", st.session_state.get("preset_key", "custom"))
    st.session_state.setdefault("preset_key", st.session_state.draft_preset)


def choose_preset():
    key = st.session_state.preset_key
    if key in PRESETS:
        set_editor(preset(key), PRESETS[key], key)


def choose_dimension():
    dimension = st.session_state.edit_dimension
    set_editor(Experiment.defaults(dimension))


def choose_scenario():
    scenario = st.session_state.edit_scenario
    set_editor(replace(Experiment(**st.session_state.draft), scenario=scenario),
               final_time=st.session_state.target_time)


def number(label, field, values, **kwargs):
    key = f"edit_{field}"
    st.session_state.setdefault(key, values[field])
    values[field] = st.number_input(label, key=key, **kwargs)


def select(label, field, values, options, **kwargs):
    key = f"edit_{field}"
    st.session_state.setdefault(key, values[field])
    values[field] = st.selectbox(label, options, key=key, **kwargs)


def advanced(values):
    st.session_state.setdefault("edit_dimension", values["dimension"])
    st.selectbox("Dimensjon", [2, 1], format_func=lambda value: f"{value}D",
                 key="edit_dimension", on_change=choose_dimension)
    dimension = values["dimension"]
    st.session_state.setdefault("edit_scenario", values["scenario"])
    st.selectbox("Forsøkstype", list(SCENARIOS[dimension]), key="edit_scenario",
                 format_func=lambda value: SCENARIOS[dimension][value], on_change=choose_scenario)
    if dimension == 1:
        select("Tidsmetode", "method", values, ["crank_nicolson", "rk4", "auto"])
        st.caption("Crank–Nicolson bevarer normen. RK4 krever små nok tidssteg. Begge har rom- og fasefeil.")
    else:
        select("Initial bølge", "wave", values, ["plane_wave", "gaussian_packet"],
               format_func=lambda value: {"plane_wave": "Bølgetog", "gaussian_packet": "Gaussisk bølgepakke"}[value])
    with st.expander("Tid og oppløsning"):
        number("Punkter i x", "nx", values, min_value=8, max_value=2048, step=8)
        if dimension == 2:
            number("Punkter i y", "ny", values, min_value=8, max_value=2048, step=8)
        number("Ønsket tidssteg (maks)", "dt", values, min_value=0.00000001, format="%.8f",
               help="Appen kan redusere dette litt for å treffe sluttiden nøyaktig. Antall steg beregnes automatisk.")
        number("Maks lagrede bilder", "frames", values, min_value=2, max_value=121, step=1)
    with st.expander("Bølge og enheter"):
        for label, field in (("Masse", "mass"), ("ħ", "hbar"), ("Breddeparameter σx", "sigma_x")):
            number(label, field, values, min_value=0.000001, format="%.6f")
        for label, field in (("Startposisjon x", "x0"), ("Bevegelsesmengde px", "px")):
            number(label, field, values, format="%.6f")
        if dimension == 2:
            number("Startposisjon y", "y0", values)
            number("Bevegelsesmengde py", "py", values)
            number("Breddeparameter σy", "sigma_y", values, min_value=0.000001)
            number("Bølgetogets innhyllingsbredde", "envelope_width", values, min_value=0.000001)
        st.caption("For Gaussformen er posisjonens standardavvik σ/2.")
    with st.expander("Potensial og geometri"):
        number("Endelig potensialstyrke", "potential_strength", values)
        number("Barrieretykkelse", "thickness", values, min_value=0.000001, format="%.6f")
        number("Harmonisk frekvens ω", "omega", values, min_value=0.000001)
        if dimension == 2:
            number("Barrierens x-posisjon", "barrier_x", values)
            number("Nominell spaltebredde", "slit_width", values, min_value=0.000001, format="%.6f")
            number("Avstand mellom spaltesentre", "slit_separation", values, min_value=0.000001)
        else:
            number("Venstre grense a", "well_left", values)
            number("Høyre grense b", "well_right", values)
            number("Eksponent n", "power", values, min_value=1, max_value=12)
    with st.expander("Boks og kantabsorpsjon"):
        for field in ("x_min", "x_max", *(("y_min", "y_max") if dimension == 2 else ())):
            number(field.replace("_", " "), field, values)
        st.session_state.setdefault("edit_absorber", values["absorber"])
        values["absorber"] = st.checkbox("Kantabsorpsjon", key="edit_absorber")
        number("Absorberens rate", "absorber_strength", values, min_value=0.0)
        number("Absorberens breddeandel", "absorber_width", values, min_value=0.000001, max_value=0.499999)
    st.session_state.draft_name = st.text_input("Navn på kjøringen", value=st.session_state.draft_name, key="edit_name")


def explore(values):
    scenario = values["scenario"]
    if scenario in {"double_slit", "single_slit"}:
        number("Spaltebredde", "slit_width", values, min_value=0.000001, format="%.3f",
               help="Nominell åpning. Den representerte åpningen på rutenettet vises under Beregningsdetaljer.")
        if scenario == "double_slit":
            number("Avstand mellom spaltene", "slit_separation", values, min_value=0.000001, format="%.3f")
    elif scenario in {"wall", "square_wall", "square_well", "power"}:
        number("Potensialstyrke", "potential_strength", values, help="For tunnelering: barrierens høyde i de valgte enhetene.")
    elif scenario == "harmonic":
        number("Frekvens ω", "omega", values, min_value=0.000001)
    else:
        number("Bevegelsesmengde", "px", values, help="Ved fast masse betyr større bevegelsesmengde høyere fart.")
        number("Bølgepakkens breddeparameter", "sigma_x", values, min_value=0.000001)


def controlled_edit(history):
    if not history:
        st.info("Kjør et forsøk under Utforsk først. Deretter kan du endre én ting og sammenlikne.")
        return None
    entries = {entry["id"]: entry for entry in history}
    if st.session_state.get("comparison_base") not in entries:
        st.session_state.pop("comparison_base", None)
    identifier = st.selectbox("Ta utgangspunkt i", list(entries), index=len(entries)-1,
                              format_func=lambda key: entries[key]["name"], key="comparison_base")
    base = entries[identifier]["run"]
    options = comparison_parameters(base.experiment)
    if st.session_state.get("one_parameter") not in options:
        st.session_state.pop("one_parameter", None)
    parameter = st.selectbox("Hva vil du endre?", list(options), format_func=options.get, key="one_parameter")
    before = getattr(base.experiment, parameter)
    key = f"one_{identifier}_{parameter}"
    if parameter == "method":
        value = st.selectbox("Ny tidsmetode", ["crank_nicolson", "rk4", "auto"],
                             index=["crank_nicolson", "rk4", "auto"].index(before), key=key)
    else:
        kwargs = {"min_value": 8, "max_value": 2048, "step": 8} if parameter in {"nx", "ny"} else {}
        if parameter in {"dt", "slit_width", "slit_separation"}:
            kwargs.update(min_value=0.00000001 if parameter == "dt" else 0.000001, format="%.8f")
        value = st.number_input("Ny verdi", value=before, key=key, **kwargs)
    final_time = float(base.times[-1])
    st.caption(f"Opprinnelig verdi: {before}. Sluttiden beholdes: {final_time:.6g}.")
    if parameter in {"nx", "ny"}:
        st.caption("Endret rutenett kan flytte spaltekanter. Kontroller de diskrete åpningene i sammenlikningen.")
    experiment = replace(base.experiment, **{parameter: value})
    name = f"{options[parameter]}: {before} → {value}"
    return experiment, final_time, name, identifier


def controls(jobs):
    with st.sidebar:
        st.title("Forsøksoppsett")
        with st.expander("Åpne lagret oppsett"):
            uploaded = st.file_uploader("JSON fra en tidligere kjøring", type=["json"])
            if st.button("Bruk oppsett", disabled=uploaded is None):
                try:
                    if uploaded.size > 1024*1024:
                        raise ValueError("Oppsettfilen kan være maksimalt 1 MiB.")
                    set_editor(Experiment.read(uploaded.getvalue().decode("utf-8")), "Importert oppsett")
                    st.session_state.work_mode = "Avansert"
                    st.rerun()
                except (ValueError, UnicodeError) as exc:
                    st.error(str(exc))
        st.radio("Arbeidsmåte", ["Utforsk", "Sammenlikn", "Avansert"], key="work_mode", horizontal=True)
        base_id = None
        if st.session_state.work_mode == "Sammenlikn":
            selection = controlled_edit(st.session_state.history)
            if selection is None:
                return None
            requested, final_time, name, base_id = selection
        else:
            presets = {**PRESETS, **({"custom": "Eget oppsett"} if st.session_state.preset_key == "custom" else {})}
            st.selectbox("Forsøk", list(presets), format_func=presets.get, key="preset_key", on_change=choose_preset)
            values = dict(st.session_state.draft)
            if st.session_state.work_mode == "Avansert":
                advanced(values)
            else:
                explore(values)
            st.session_state.setdefault("edit_final_time", st.session_state.target_time)
            final_time = st.number_input("Fysisk sluttid", min_value=0.00000001, format="%.6f", key="edit_final_time",
                                         help="Hvor lenge fysikken utvikles, ikke hvor fort bildene spilles av. Antall beregningssteg tilpasses automatisk.")
            st.session_state.target_time = final_time
            st.session_state.draft = values
            requested = Experiment(**values)
            name = st.session_state.draft_name
        try:
            experiment = at_final_time(requested, final_time)
            config = experiment.configuration()
            details = boundary_details(config, get_barrier_mask(config))
        except (ValueError, TypeError, OverflowError) as exc:
            st.error(f"Kontroller oppsettet: {exc}")
            return None
        if st.button("Kjør simulering", type="primary", disabled=jobs.busy()):
            try:
                st.session_state.pending = jobs.start(experiment)
                st.session_state.pending_name = name
                st.session_state.pending_base = base_id
                st.rerun()
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        if jobs.busy() and not st.session_state.get("pending"):
            st.info("En annen fane beregner. Én kjøring tillates om gangen.")
    return experiment, config, details
