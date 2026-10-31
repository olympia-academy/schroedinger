"""Separate the 17% screen-profile difference into controlled comparisons.

Run from the repository root after installing the package:
python examples/explain_grid_difference.py
The production propagators and default masks are not modified. Custom masks
are experimental controls that preserve measured Dirichlet boundary nodes.
"""
import argparse
import json
from pathlib import Path
from time import perf_counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from schroedinger import get_wave_packet, get_potential, get_barrier_mask, simulate
from double_slit_sensitivity import configuration, screen_profile, BASE_DT


CASES = {
    "x_only": (768, 256, BASE_DT/2, None),
    "y_only": (512, 384, BASE_DT/2, None),
    "common_A": (512, 768, BASE_DT/2, "A"),
    "common_B": (512, 768, BASE_DT/2, "B"),
    "common_A_half_dt": (512, 768, BASE_DT/4, "A"),
    "common_B_half_dt": (512, 768, BASE_DT/4, "B"),
    "fine_half_dt": (768, 384, BASE_DT/4, None),
}


def boundary_geometry(config, mask):
    """Record excluded nodes that bound connected sine intervals.

    Width is the distance between zero-value nodes, NOT open count * dy.
    """
    iv = config.initial_values
    blocked_x = np.flatnonzero(np.any(mask, axis=0))
    column = blocked_x[len(blocked_x)//2]
    opening = ~mask[:, column]
    edges = np.flatnonzero(np.diff(np.r_[False, opening, False]))
    bounds = [[float(iv.y_grid[start-1]), float(iv.y_grid[stop])]
              for start, stop in edges.reshape(-1, 2)]
    return {"wall_faces": iv.x_grid[blocked_x[[0, -1]]].tolist(),
            "opening_bounds": bounds,
            "opening_widths": [hi-lo for lo, hi in bounds],
            "opening_centres": [(hi+lo)/2 for lo, hi in bounds]}


def matched_mask(config, geometry):
    """Same boundary coordinates on a common lattice, checked explicitly."""
    iv = config.initial_values
    for coordinate in geometry["wall_faces"]:
        if not np.any(np.isclose(iv.x_grid, coordinate, rtol=0, atol=1e-12)):
            raise ValueError("A wall face is not represented on this grid")
    for interval in geometry["opening_bounds"]:
        for coordinate in interval:
            if not np.any(np.isclose(iv.y_grid, coordinate, rtol=0, atol=1e-12)):
                raise ValueError("An opening boundary is not represented on this grid")
    x, y = np.meshgrid(iv.x_grid, iv.y_grid)
    lo, hi = geometry["wall_faces"]
    wall = (x >= lo-1e-12) & (x <= hi+1e-12)
    opening = np.zeros_like(wall)
    for lo, hi in geometry["opening_bounds"]:
        # Boundary nodes themselves are excluded: psi=0 there.
        opening |= (y > lo+1e-12) & (y < hi-1e-12)
    mask = wall & ~opening
    measured = boundary_geometry(config, mask)
    if not np.allclose(measured["opening_bounds"], geometry["opening_bounds"], atol=1e-12, rtol=0):
        raise ValueError("The control mask did not retain its boundary coordinates")
    return mask


def metrics(profile, reference):
    profile, reference = np.asarray(profile), np.asarray(reference)
    return {"relative_l1": float(np.sum(abs(profile-reference))/np.sum(abs(reference))),
            "shape_l1": float(np.sum(abs(profile/profile.sum()-reference/reference.sum()))),
            "area_ratio": float(profile.sum()/reference.sum())}


def summarize(data, output):
    profiles = {name: np.array(value) for name, value in data["profiles"].items()}
    pairs = [("A_original", "B_original"), ("x_only", "A_original"),
             ("y_only", "B_original"), ("A_original", "common_A"),
             ("common_A", "common_B"), ("B_original", "common_B"),
             ("common_A", "common_A_half_dt"), ("common_B", "common_B_half_dt"),
             ("B_original", "fine_half_dt")]
    comparisons = []
    for case, reference in pairs:
        entry = {"case": case, "reference": reference, **metrics(profiles[case], profiles[reference])}
        comparisons.append(entry)
    # Bound interpolation/resampling effects using a fixed fine-grid profile.
    measurement = {}
    y = np.array(data["y"])
    for geometry in ("A", "B"):
        native = data["native"][f"common_{geometry}"]
        native_y, native_q = np.array(native["y"]), np.array(native["profile"])
        resampled = []
        for ny in (256, 384):
            grid = np.linspace(-10, 10, ny, endpoint=False)
            coarse_q = np.interp(grid, native_y, native_q)
            resampled.append(np.interp(y, grid, coarse_q))
        measurement[geometry] = metrics(resampled[0], resampled[1])
    data["comparisons"] = comparisons
    data["y_resampling_control"] = measurement
    output.joinpath("study.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = ["| Profile | Reference | Relative L1 | Shape L1 | Area ratio |",
             "|---|---|---:|---:|---:|"]
    for row in comparisons:
        lines.append(f"| {row['case']} | {row['reference']} | {row['relative_l1']:.2%} | "
                     f"{row['shape_l1']:.2%} | {row['area_ratio']:.6f} |")
    for name, values in measurement.items():
        lines.append(f"\nY-resampling control, geometry {name}: {values['relative_l1']:.2%}")
    output.joinpath("table.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
    for name in ("A_original", "B_original", "x_only", "y_only"):
        axes[0].plot(y, profiles[name], label=name, linewidth=1)
    for name in ("common_A", "common_B", "common_A_half_dt", "common_B_half_dt"):
        axes[1].plot(y, profiles[name], label=name, linewidth=1)
    axes[0].set_title("Refine x and y separately")
    axes[1].set_title("Same grid (512 x 768), different opening geometry")
    for ax in axes:
        ax.set_xlabel("y in fixed screen slab 4 <= x <= 8")
        ax.legend(fontsize=7)
    axes[0].set_ylabel("Slab probability / incident probability per unit y")
    fig.tight_layout()
    fig.savefig(output / "attribution.png", dpi=140)
    plt.close(fig)
    print("\n".join(lines), flush=True)


def run(output, source):
    output.mkdir(parents=True, exist_ok=True)
    original = json.loads(source.read_text(encoding="utf-8"))
    geometries = {}
    for name, nx, ny in (("A", 512, 256), ("B", 768, 384)):
        config = configuration({"nx": nx, "ny": ny, "dt": BASE_DT/2})
        geometries[name] = boundary_geometry(config, get_barrier_mask(config))
    data = {"source_study": str(source), "time": original["final_time"], "geometry": geometries,
            "y": original["y"], "records": [], "native": {},
            "profiles": {"A_original": original["profiles"]["dt_half"],
                         "B_original": original["profiles"]["grid_fine"]}}
    for name, (nx, ny, dt, geometry) in CASES.items():
        start = perf_counter()
        config = configuration({"nx": nx, "ny": ny, "dt": dt})
        mask = get_barrier_mask(config) if geometry is None else matched_mask(config, geometries[geometry])
        result = simulate(get_wave_packet(config), get_potential(config), config, mask)
        y, profile, incident = screen_profile(result, config)
        data["profiles"][name] = profile.tolist()
        iv = config.initial_values
        weights = np.maximum(0, np.minimum(iv.x_grid+iv.dx/2, 8)-np.maximum(iv.x_grid-iv.dx/2, 4))
        native_profile = result.density(-1) @ weights / incident
        data["native"][name] = {"y": iv.y_grid.tolist(), "profile": native_profile.tolist()}
        data["records"].append({"case": name, "nx": nx, "ny": ny, "dt": dt,
                                "geometry": boundary_geometry(config, mask),
                                "probability": float(result.norms[-1]),
                                "absorbed": float(result.absorbed[-1]),
                                "budget_error": float(np.max(abs(result.norms+result.absorbed-1))),
                                "seconds": perf_counter()-start})
        output.joinpath("study.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"{name}: {perf_counter()-start:.1f}s", flush=True)
    summarize(data, output)
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/grid-attribution"))
    parser.add_argument("--source", type=Path, default=Path("docs/data/double-slit-sensitivity.json"))
    args = parser.parse_args()
    run(args.output, args.source)
