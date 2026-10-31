"""Reproduce a controlled sensitivity study of the default double slit.

One case runs at a time; only initial/final density frames are retained.
No GUI is opened. Run from the repository root after installing the package:
python examples/double_slit_sensitivity.py --output outputs/sensitivity
Use --cases baseline dt_half for a smaller selection (baseline is required).
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import platform
from time import perf_counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
from schroedinger import Config2D, get_wave_packet, get_potential, get_barrier_mask, simulate


FINAL_TIME = 7.03125
BASE_DT = 0.0390625
CASES = {
    "baseline": {},
    "dt_half": {"dt": BASE_DT/2},
    "dt_quarter": {"dt": BASE_DT/4},
    # Spatial comparisons share dt with dt_half; geometry is re-rasterized.
    "grid_coarse": {"nx": 256, "ny": 128, "dt": BASE_DT/2},
    "grid_fine": {"nx": 768, "ny": 384, "dt": BASE_DT/2},
    # Preserve dx, dy when enlarging the box. The incident train is uniform y.
    "larger_box": {"nx": 768, "ny": 384, "x_min": -25., "x_max": 35.,
                   "y_min": -15., "y_max": 15.},
    "no_absorber": {"enabled": False},
    "weaker_absorber": {"strength": 15.},
    "stronger_absorber": {"strength": 60.},
    "narrow_absorber": {"width_frac": 0.05},
    "wide_absorber": {"width_frac": 0.15},
}


def configuration(changes):
    config = Config2D()
    config.initial_values.wave_type = "plane_wave"
    for name, value in changes.items():
        target = config.absorber if name in {"enabled", "strength", "width_frac"} else config.initial_values
        setattr(target, name, value)
    steps = round(FINAL_TIME/config.initial_values.dt)
    assert np.isclose(steps*config.initial_values.dt, FINAL_TIME)
    config.simulation_params.steps = steps
    config.simulation_params.save_every = steps
    config.simulation_params.store_density = True
    config.simulation_params.progress = False
    return config.validate()


def screen_profile(result, config):
    """Integrate a fixed physical slab 4<=x<=8, correcting edge cell weights.

    Divide by incident probability per unit y at y=0. This removes the
    trivial 1/Ly normalization change for a wider uniform incident train.
    It does NOT make different finite boxes the same physical problem.
    """
    iv = config.initial_values
    weights = np.maximum(0, np.minimum(iv.x_grid+iv.dx/2, 8)
                         - np.maximum(iv.x_grid-iv.dx/2, 4))
    incident_per_y = float(result.density(0)[np.argmin(abs(iv.y_grid))].sum()*iv.dx)
    profile = result.density(-1) @ weights / incident_per_y
    # Compare only the same central region, independent of box size.
    y = np.linspace(-6, 6, 193)
    return y, np.interp(y, iv.y_grid, profile), incident_per_y


def run_study(names, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    records = []
    profiles = {}
    for name in names:
        start = perf_counter()
        config = configuration(CASES[name])
        mask = get_barrier_mask(config)
        result = simulate(get_wave_packet(config), get_potential(config), config, mask)
        y, profile, incident = screen_profile(result, config)
        profiles[name] = profile
        iv = config.initial_values
        wall_column = np.argmin(abs(iv.x_grid-config.barrier.barrier_x))
        opening = ~mask[:, wall_column]
        edges = np.flatnonzero(np.diff(np.r_[False, opening, False]))
        # Node counts * dy are raster measures, NOT exact continuum widths.
        widths = [(stop-first)*iv.dy for first, stop in edges.reshape(-1, 2)]
        record = {
            "case": name, "config": asdict(config), "dt": iv.dt, "dx": iv.dx, "dy": iv.dy,
            "time": float(result.times[-1]), "probability": float(result.norms[-1]),
            "absorbed": float(result.absorbed[-1]),
            "budget_error": float(np.max(abs(result.norms+result.absorbed-1))),
            "initial_projection_loss": result.initial_projection_loss,
            "incident_probability_per_y": incident,
            "slit_node_widths": widths,
            "wall_node_width": float(np.any(mask, axis=0).sum()*iv.dx),
            "seconds": perf_counter()-start,
        }
        records.append(record)
        print(f"{name}: {record['seconds']:.1f}s, P={record['probability']:.6f}", flush=True)
        # Save incrementally so completed cases survive an interrupted run.
        data = {"final_time": FINAL_TIME, "screen_x": [4, 8], "comparison_y": [-6, 6],
                "python": platform.python_version(), "numpy": np.__version__,
                "scipy": scipy.__version__, "matplotlib": matplotlib.__version__,
                "y": y.tolist(), "profiles": {k: v.tolist() for k, v in profiles.items()},
                "records": records}
        (output / "study.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    def distance(a, b):
        return float(np.sum(abs(a-b))/np.sum(abs(b)))

    lines = ["| Case | P remaining | Absorbed | Profile L1 vs baseline | Shape L1 vs baseline |",
             "|---|---:|---:|---:|---:|"]
    base = profiles["baseline"]
    for record in records:
        profile = profiles[record["case"]]
        record["profile_l1_vs_baseline"] = distance(profile, base)
        record["shape_l1_vs_baseline"] = distance(profile/profile.sum(), base/base.sum())
        lines.append(f"| {record['case']} | {record['probability']:.6f} | {record['absorbed']:.6f} | "
                     f"{record['profile_l1_vs_baseline']:.2%} | {record['shape_l1_vs_baseline']:.2%} |")
    lines.extend(["", "Paired profile L1 comparisons (same reference denominator):"])
    for case, reference in (("dt_half", "dt_quarter"), ("grid_coarse", "dt_half"),
                            ("dt_half", "grid_fine")):
        if case in profiles and reference in profiles:
            lines.append(f"- {case} vs {reference}: {distance(profiles[case], profiles[reference]):.2%}")
    (output / "table.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    (output / "study.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    groups = [("Time and grid", ["baseline", "dt_half", "dt_quarter", "grid_coarse", "grid_fine"]),
              ("Box and absorber", [n for n in names if n not in {"dt_half", "dt_quarter", "grid_coarse", "grid_fine"}])]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
    for ax, (title, group) in zip(axes, groups):
        for name in group:
            if name in profiles:
                ax.plot(y, profiles[name], label=name, linewidth=1)
        ax.set(title=title, xlabel="y in screen slab 4 <= x <= 8")
        ax.legend(fontsize=7)
    axes[0].set_ylabel("Slab probability / incident probability per unit y")
    fig.suptitle(f"Double slit at t={FINAL_TIME}; sensitivity, not a convergence certificate")
    fig.tight_layout()
    fig.savefig(output / "profiles.png", dpi=140)
    plt.close(fig)
    print("\n".join(lines), flush=True)
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", nargs="+", choices=tuple(CASES), default=list(CASES))
    parser.add_argument("--output", type=Path, default=Path("outputs/sensitivity"))
    args = parser.parse_args()
    if "baseline" not in args.cases:
        parser.error("--cases must include baseline")
    run_study(args.cases, args.output)
