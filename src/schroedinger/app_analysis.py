"""Density-only measurements and controlled numerical refinement for the lab."""
from dataclasses import replace

import numpy as np

from .app_presets import at_final_time
from .potentials import get_barrier_mask


def nearest_indices(saved, requested):
    """Select real saved frames, never interpolate in time; ties choose earlier."""
    saved, requested = np.asarray(saved), np.asarray(requested)
    right = np.clip(np.searchsorted(saved, requested), 0, len(saved)-1)
    left = np.maximum(0, right-1)
    return np.where(abs(saved[left]-requested) <= abs(saved[right]-requested), left, right)


def measurements(run, screen_x=None):
    config = run.experiment.configuration()
    iv, experiment = config.initial_values, run.experiment
    result = {}
    faces = None
    if experiment.dimension == 2 and experiment.scenario in {"double_slit", "single_slit", "wall"}:
        mask = get_barrier_mask(config)
        if mask is not None:
            columns = np.flatnonzero(np.any(mask, axis=0))
            faces = iv.x_grid[columns[[0, -1]]]
        else:
            faces = [experiment.barrier_x-experiment.thickness/2,
                     experiment.barrier_x+experiment.thickness/2]
    elif experiment.dimension == 1 and experiment.scenario == "square_wall":
        faces = ([experiment.well_right, experiment.well_right+experiment.thickness]
                 if experiment.px >= 0 else
                 [experiment.well_left-experiment.thickness, experiment.well_left])
    if faces is not None:
        left, right = iv.x_grid < faces[0], iv.x_grid > faces[1]
        middle = ~(left | right)
        result["regions"] = {
            name: np.sum(run.densities[..., selected], axis=tuple(range(1, run.densities.ndim)),
                         dtype=np.float64).tolist()
            for name, selected in (("left", left), ("barrier", middle), ("right", right))}
        result["regions"] = {name: (np.array(values)*config.cell_volume).tolist()
                             for name, values in result["regions"].items()}
        result["faces"] = list(map(float, faces))
    if experiment.dimension == 2:
        if screen_x is None:
            screen_x = float(np.clip(experiment.barrier_x+0.25*(iv.x_max-experiment.barrier_x),
                                     iv.x_grid[0], iv.x_grid[-1]))
        if not iv.x_grid[0] <= screen_x <= iv.x_grid[-1]:
            raise ValueError("Profilens x-posisjon må ligge inne i begge rutenettene.")
        column = int(np.argmin(abs(iv.x_grid-screen_x)))
        result["profile"] = run.densities[:, :, column].tolist()
        result.update(screen_x=float(iv.x_grid[column]), y=iv.y_grid.tolist())
    return result


def refined_experiment(experiment, kind):
    """Keep final time fixed and bound stored frames when refining the grid."""
    if kind == "dt":
        refined = at_final_time(replace(experiment, dt=experiment.dt/2), experiment.dt*experiment.steps)
    elif kind == "grid":
        nx = 2*(experiment.nx-1)+1 if experiment.dimension == 1 else 2*experiment.nx
        ny = experiment.ny if experiment.dimension == 1 else 2*experiment.ny
        cells = nx*(ny if experiment.dimension == 2 else 1)
        cap = min(experiment.frames, 128*1024**2//(4*cells))
        refined = replace(experiment, nx=nx, ny=ny, frames=cap)
    else:
        raise ValueError("Ukjent kontroll.")
    refined.configuration()
    return refined


def density_difference(first, second):
    """Final density L1 difference, interpolating space only onto first's grid."""
    a, b = first.experiment, second.experiment
    if a.dimension != b.dimension or any(getattr(a, key) != getattr(b, key)
            for key in (("x_min", "x_max", "y_min", "y_max") if a.dimension == 2 else ("x_min", "x_max"))):
        raise ValueError("Denne kontrollen krever samme dimensjon og boks.")
    if not np.isclose(first.times[-1], second.times[-1], rtol=1e-12, atol=1e-12):
        raise ValueError("Denne kontrollen krever samme fysiske sluttid.")
    ca, cb = a.configuration(), b.configuration()
    xa, xb = ca.initial_values.x_grid, cb.initial_values.x_grid
    fine = second.densities[-1].astype(float)
    if a.dimension == 1:
        mapped = np.interp(xa, xb, fine)
    else:
        ya, yb = ca.initial_values.y_grid, cb.initial_values.y_grid
        along_x = np.array([np.interp(xa, xb, row) for row in fine])
        mapped = np.array([np.interp(ya, yb, column) for column in along_x.T]).T
    l1 = float(np.sum(abs(first.densities[-1]-mapped))*ca.cell_volume)
    return {"density_l1": l1,
            "probability_difference": abs(first.summary["probability"][-1]-second.summary["probability"][-1]),
            "geometry_changed": first.summary["boundaries"] != second.summary["boundaries"]}
