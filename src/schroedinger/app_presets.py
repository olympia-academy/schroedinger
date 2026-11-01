"""Presets and controlled edits; no changes to the propagation algorithms."""
from dataclasses import asdict, replace
import math

from .app_model import Experiment


PRESETS = {
    "double_slit": "Dobbeltspalte (2D)",
    "single_slit": "Enkeltspalte (2D)",
    "tunneling": "Tunnelering (1D)",
    "free": "Fri bølgepakke (2D)",
    "free_reference": "Fri bølgepakke – referanse (1D)",
}


def preset(name):
    if name == "double_slit":
        return Experiment()
    if name == "single_slit":
        return replace(Experiment(), scenario="single_slit")
    if name == "tunneling":
        return Experiment.defaults(1)
    if name == "free":
        return replace(Experiment(), scenario="free", wave="gaussian_packet")
    if name == "free_reference":
        return replace(Experiment.defaults(1), scenario="free", nx=1024,
                       x_min=-12.0, x_max=12.0, mass=1.0, hbar=1.0,
                       x0=-4.0, px=2.0, sigma_x=2.0, dt=0.002, steps=1000,
                       absorber=False)
    raise ValueError("Ukjent forsøksoppsett.")


def at_final_time(experiment, final_time):
    """Use equal steps, no larger than requested dt, landing exactly at T.

    The returned Experiment contains actual dt/steps for exports and workers.
    The editor retains the requested maximum dt separately.
    """
    if not math.isfinite(final_time) or final_time <= 0:
        raise ValueError("Sluttiden må være et endelig, positivt tall.")
    if not math.isfinite(experiment.dt) or experiment.dt <= 0:
        raise ValueError("Tidssteget må være endelig og positivt.")
    ratio = final_time/experiment.dt
    if not math.isfinite(ratio) or ratio > 200000:
        raise ValueError("Sluttiden krever for mange steg. Velg kortere tid eller et større tillatt tidssteg.")
    nearest = round(ratio)
    steps = nearest if math.isclose(ratio, nearest, rel_tol=1e-12, abs_tol=1e-12) else math.ceil(ratio)
    return replace(experiment, steps=max(1, steps), dt=final_time/max(1, steps))


def changes(first, second):
    before, after = asdict(first), asdict(second)
    return [{"Parameter": name, "Før": str(before[name]), "Etter": str(value)}
            for name, value in after.items() if before[name] != value]


def comparison_parameters(experiment):
    options = {"px": "Bevegelsesmengde", "dt": "Tidssteg", "nx": "Punkter i x"}
    if experiment.dimension == 2:
        options["ny"] = "Punkter i y"
    if experiment.scenario in {"single_slit", "double_slit"}:
        options = {"slit_width": "Spaltebredde", **options}
    if experiment.scenario == "double_slit":
        options["slit_separation"] = "Spalteavstand"
    if experiment.scenario in {"wall", "square_wall", "square_well", "power"}:
        options["potential_strength"] = "Potensialstyrke"
    if experiment.dimension == 1:
        options["method"] = "Tidsmetode"
    return options
