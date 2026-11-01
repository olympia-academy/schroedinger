"""Free-packet analysis of saved densities, with explicit reference limitations."""
import numpy as np

from .wavepacket import position_moments, free_gaussian_moments, gaussian_outside_probability

TAIL_WARNING = 1e-8


def analyze_free_packet(run):
    experiment = run.experiment
    if experiment.dimension != 1 or experiment.scenario != "free":
        raise ValueError("This reference is for the existing 1D free Gaussian only.")
    config = experiment.configuration()
    iv = config.initial_values
    numerical = position_moments(run.densities, iv.x_grid)
    sigma0 = experiment.sigma_x/2
    reference = free_gaussian_moments(run.times, x0=experiment.x0, p0=experiment.px,
                                      sigma0=sigma0, mass=experiment.mass, hbar=experiment.hbar)
    tail = gaussian_outside_probability(reference["mean_x"], reference["sigma_x"],
                                        iv.x_min-iv.dx, iv.x_max+iv.dx)
    reasons = []
    if experiment.absorber and experiment.absorber_strength > 0:
        reasons.append("Kantabsorpsjon er aktiv. Momentene beskriver den gjenværende sannsynligheten; referansen har ingen absorpsjon.")
    if float(np.max(tail)) > TAIL_WARNING:
        reasons.append("Referansepakken når for nær ytterkantene i løpet av kjøringen. Den analytiske løsningen gjelder uendelig rom, mens simuleringen har reflekterende Dirichlet-rand.")
    if np.any(numerical["probability"] <= 0):
        reasons.append("En eller flere rammer har null lagret sannsynlighet. Middelposisjon og spredning er da udefinert.")
    usable = not reasons
    summary = {
        "reference_usable": usable, "reasons": reasons, "initial_position_std": sigma0,
        "max_reference_outside_probability": float(np.max(tail)),
        "tail_warning_threshold": TAIL_WARNING,
        "max_probability_drift": float(np.max(abs(np.asarray(run.summary["probability"])-run.summary["probability"][0]))),
        "reference_assumptions": "Free unchirped minimum-uncertainty Gaussian on the infinite line; no absorption.",
        "moment_normalization": "Normalized by probability remaining in the box at each saved time.",
    }
    if usable:
        summary.update(max_mean_error=float(np.max(abs(numerical["mean_x"]-reference["mean_x"]))),
                       max_sigma_error=float(np.max(abs(numerical["sigma_x"]-reference["sigma_x"]))))
    return {"times": run.times, "numerical": numerical, "reference": reference,
            "outside_probability": tail, "summary": summary}


def show_free_packet(run, name, identifier):
    if run.experiment.dimension != 1 or run.experiment.scenario != "free":
        return
    import altair as alt
    import pandas as pd
    import streamlit as st

    analysis = analyze_free_packet(run)
    measured, reference, summary = analysis["numerical"], analysis["reference"], analysis["summary"]
    index = pd.Index(analysis["times"], name="Fysisk tid")
    with st.expander("Fri bølgepakke: middelposisjon og spredning", expanded=True):
        st.write(f"Analyse av: {name}")
        st.caption("Middelposisjonen ⟨x⟩ er pakkens tyngdepunkt. Standardavviket Δx beskriver dens romlige spredning. Kurvene bruker alle lagrede tidspunkter i den valgte kjøringen.")
        for reason in summary["reasons"]:
            st.warning(reason)
        for field, label in (("mean_x", "Middelposisjon ⟨x⟩"), ("sigma_x", "Standardavvik Δx")):
            curves = {"Numerisk": measured[field]}
            if summary["reference_usable"]:
                curves["Analytisk, uendelig rom"] = reference[field]
            st.write(label)
            data = pd.DataFrame(curves, index=index).rename_axis("time").reset_index().melt(
                id_vars="time", var_name="solution", value_name="value")
            # No wheel-bound zoom: scrolling the page must not distort the axes.
            chart = alt.Chart(data).mark_line().encode(
                x=alt.X("time:Q", title="Fysisk tid"),
                y=alt.Y("value:Q", title=label, scale=alt.Scale(zero=False)),
                color=alt.Color("solution:N", title="Løsning", scale=alt.Scale(
                    domain=list(curves), range=["#176b8c", "#c87917"][:len(curves)])),
                strokeDash=alt.StrokeDash("solution:N", title="Løsning", scale=alt.Scale(
                    domain=list(curves), range=[[1, 0], [6, 4]][:len(curves)])),
                tooltip=[alt.Tooltip("time:Q", title="Fysisk tid"),
                         alt.Tooltip("solution:N", title="Løsning"),
                         alt.Tooltip("value:Q", title=label, format=".6g")],
            ).properties(height=220)
            st.altair_chart(chart, width="stretch")
        if summary["reference_usable"]:
            st.write("Avvik fra den analytiske referansen, største absolutte avvik over lagrede tidspunkter:")
            st.dataframe([{"Størrelse": "Middelposisjon", "Maks absolutt avvik": summary["max_mean_error"]},
                          {"Størrelse": "Standardavvik", "Maks absolutt avvik": summary["max_sigma_error"]}], hide_index=True)
            st.caption(f"Maks normdrift (kompleks tilstand): {summary['max_probability_drift']:.2e}. "
                       f"Største estimerte sannsynlighet utenfor boksen for referansepakken: {summary['max_reference_outside_probability']:.2e}.")
        with st.expander("Referanse og forutsetninger"):
            st.latex(r"\langle x\rangle(t)=x_0+\frac{p_0}{m}t,\qquad "
                     r"\Delta x(t)=\sqrt{\Delta x_0^2+\left(\frac{\hbar t}{2m\Delta x_0}\right)^2}")
            st.write(f"Her er Δx₀ = {summary['initial_position_std']:g}. I kodekonvensjonen er dette halvparten av breddeparameteren σx.")
            st.caption("Referansen gjelder en fri Gauss-pakke uten initial posisjon–bevegelsesmengde-korrelasjon. Ingen absorber eller ytterkant inngår i løsningen. Grensen for halemasse er et varselkriterium, ikke en garanti for nøyaktighet. Normbevaring alene dokumenterer ikke konvergens.")
            st.caption("Momentene er betinget på at partikkelen fortsatt er i boksen. Full bølgefunksjon og fase kan ha feil selv om disse to momentene stemmer. Tettheter lagres som float32; summering skjer i float64. Alle størrelser bruker modellens valgte enheter.")
        exported = pd.DataFrame({"time": analysis["times"], "probability_from_density": measured["probability"],
                                 "mean_x": measured["mean_x"], "position_std": measured["sigma_x"],
                                 "reference_mean_x": reference["mean_x"], "reference_position_std": reference["sigma_x"],
                                 "reference_outside_probability": analysis["outside_probability"],
                                 "reference_usable": summary["reference_usable"]})
        st.download_button("Last ned middelposisjon og spredning", exported.to_csv(index=False),
                           "free-wavepacket-moments.csv", "text/csv", key=f"moments_{identifier}")
