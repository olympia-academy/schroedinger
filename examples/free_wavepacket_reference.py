"""Reproduce the free-packet reference figure, moments CSV and numerical report.

Run from the repository root:
    python examples/free_wavepacket_reference.py --output outputs/free-wavepacket-reference
"""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import numpy as np
import scipy

from schroedinger.app_model import calculate
from schroedinger.app_presets import preset
from schroedinger.app_wavepacket import analyze_free_packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/free-wavepacket-reference"),
                        help="Output prefix for PNG, JSON and CSV")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    experiment = preset("free_reference")
    cases, default = [], None
    for name, config in [("coarse_grid", replace(experiment, nx=512)),
                         ("default", experiment),
                         ("fine_grid", replace(experiment, nx=2047)),
                         ("half_dt", replace(experiment, dt=experiment.dt/2, steps=experiment.steps*2))]:
        run = calculate(config)
        analysis = analyze_free_packet(run)
        cases.append({"name": name, "experiment": asdict(config),
                      "dx": config.configuration().initial_values.dx, "summary": analysis["summary"]})
        if name == "default":
            default = analysis
    t, measured, exact = default["times"], default["numerical"], default["reference"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")
    for column, (field, label) in enumerate((("mean_x", "Mean position ⟨x⟩"), ("sigma_x", "Position standard deviation Δx"))):
        axes[0, column].plot(t, measured[field], label="Numerical, Crank–Nicolson", color="#176b8c")
        axes[0, column].plot(t, exact[field], "--", label="Analytic, infinite line", color="#c87917")
        axes[0, column].set(ylabel=label, xlabel="Time")
        axes[0, column].legend()
        axes[1, column].plot(t, measured[field]-exact[field], color="#176b8c")
        axes[1, column].axhline(0, lw=0.8, color="#9b9b9b")
        axes[1, column].set(ylabel="Numerical − analytic", xlabel="Time")
    for ax in axes.flat:
        ax.grid(alpha=0.2)
    fig.suptitle("Free Gaussian packet · no absorption · boundaries far from packet")
    fig.savefig(args.output.with_suffix(".png"), dpi=150)
    plt.close(fig)
    columns = np.column_stack([t, measured["probability"], measured["mean_x"], measured["sigma_x"],
                               exact["mean_x"], exact["sigma_x"], default["outside_probability"]])
    np.savetxt(args.output.with_suffix(".csv"), columns, delimiter=",", comments="",
               header="time,probability_from_density,mean_x,position_std,reference_mean_x,reference_position_std,reference_outside_probability")
    report = {"schema_version": 1, "python": platform.python_version(), "numpy": np.__version__,
              "scipy": scipy.__version__, "convention": "psi ~ exp(-((x-x0)/width)^2); position_std=width/2",
              "limitations": "Moment checks only; infinite-line reference without absorption; boundary-tail test is a warning, not an error bound.",
              "cases": cases}
    args.output.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps([{key: case[key] for key in ("name", "dx", "summary")} for case in cases], indent=2))
    print(f"Saved PNG, JSON and CSV: {args.output}")


if __name__ == "__main__":
    main()
