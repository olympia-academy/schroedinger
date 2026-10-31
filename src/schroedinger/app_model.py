"""Portable experiment settings and results, independent of the web UI."""
from dataclasses import asdict, dataclass, fields
import io
import json
import platform

from matplotlib.figure import Figure
import numpy as np
import scipy

from .config import Config1D, Config2D
from .cli import report
from .potentials import get_barrier_mask, get_potential
from .states import get_wave_packet
from .solvers import simulate


@dataclass
class Experiment:
    dimension: int = 2
    scenario: str = "double_slit"
    wave: str = "plane_wave"
    method: str = "auto"
    nx: int = 512
    ny: int = 256
    dt: float = 0.0390625
    steps: int = 180
    frames: int = 101
    mass: float = 10.0
    hbar: float = 1.0
    px: float = 20.0
    py: float = 0.0
    x0: float = -8.0
    y0: float = 0.0
    sigma_x: float = 1.0
    sigma_y: float = 1.0
    envelope_width: float = 4.0
    barrier_x: float = 0.0
    thickness: float = 0.4
    slit_width: float = 0.6
    slit_separation: float = 3.0
    potential_strength: float = 22.0
    omega: float = 1.0
    absorber: bool = True
    absorber_strength: float = 30.0
    absorber_width: float = 0.1
    x_min: float = -15.0
    x_max: float = 25.0
    y_min: float = -10.0
    y_max: float = 10.0
    well_left: float = -10.0
    well_right: float = 5.0
    power: int = 2

    @classmethod
    def defaults(cls, dimension):
        if dimension == 1:
            return cls(dimension=1, scenario="square_wall", method="crank_nicolson",
                       nx=512, dt=0.002, steps=3500, potential_strength=24.0,
                       thickness=0.5, x_min=-10.0, x_max=10.0, absorber=False)
        return cls()

    @classmethod
    def read(cls, text):
        try:
            payload = json.loads(text)
            if payload.get("schema_version") != 1:
                raise ValueError("Oppsettet må ha schema_version=1.")
            values = payload["experiment"]
            known = {field.name for field in fields(cls)}
            if not isinstance(values, dict) or set(values)-known:
                raise ValueError("Oppsettet inneholder ukjente parametere.")
            experiment = cls(**values)
            experiment.configuration()
            return experiment
        except (TypeError, KeyError, AttributeError) as exc:
            raise ValueError("Filen er ikke et gyldig forsøksoppsett.") from exc

    def configuration(self):
        if type(self.dimension) is not int or self.dimension not in (1, 2):
            raise ValueError("Dimensjonen må være 1 eller 2.")
        if type(self.frames) is not int or not 2 <= self.frames <= 121:
            raise ValueError("Velg mellom 2 og 121 lagrede bilder.")
        if type(self.absorber) is not bool:
            raise ValueError("Absorber må være på eller av.")
        if any(type(value) is not int or not 8 <= value <= 2048 for value in (self.nx, self.ny)):
            raise ValueError("Appen støtter 8–2048 punkter per retning.")
        if type(self.power) is not int or not 1 <= self.power <= 12:
            raise ValueError("Appen støtter heltallig eksponent fra 1 til 12.")
        for name in ("mass", "hbar", "sigma_x", "sigma_y", "envelope_width", "thickness", "slit_width", "slit_separation", "omega"):
            if not np.isfinite(getattr(self, name)) or getattr(self, name) < 0.000001:
                raise ValueError(f"{name} må være minst 0.000001 i appen.")
        if not np.isfinite(self.dt) or self.dt < 0.00000001:
            raise ValueError("dt må være minst 0.00000001 i appen.")
        if not 0.000001 <= self.absorber_width <= 0.499999:
            raise ValueError("Absorberens breddeandel må være mellom 0.000001 og 0.499999.")
        config = Config1D() if self.dimension == 1 else Config2D()
        iv, c, sp, bg = config.initial_values, config.constants, config.simulation_params, config.barrier
        iv.nx, iv.x_min, iv.x_max, iv.dt = self.nx, self.x_min, self.x_max, self.dt
        c.mass, c.h_bar = self.mass, self.hbar
        c.potential_type, c.potential_strength = self.scenario, self.potential_strength
        bg.omega = self.omega
        if self.dimension == 2:
            iv.ny, iv.y_min, iv.y_max = self.ny, self.y_min, self.y_max
            iv.initial_position, iv.initial_momentum = (self.x0, self.y0), (self.px, self.py)
            iv.sigma_x, iv.sigma_y = self.sigma_x, self.sigma_y
            iv.wave_type, iv.plane_wave_envelope_width = self.wave, self.envelope_width
            bg.barrier_x, bg.barrier_thickness = self.barrier_x, self.thickness
            bg.slit_width, bg.slit_separation = self.slit_width, self.slit_separation
        else:
            iv.initial_position, iv.initial_momentum = self.x0, self.px
            iv.initial_position_uncertainty = self.sigma_x
            bg.a, bg.b, bg.d, bg.n = self.well_left, self.well_right, self.thickness, self.power
        sp.steps, sp.method, sp.progress, sp.store_density = self.steps, self.method, False, True
        # ceil(steps / (frames-1)) guarantees that both endpoints fit in the cap.
        if type(self.steps) is not int or not 1 <= self.steps <= 200000:
            raise ValueError("Velg mellom 1 og 200000 tidssteg.")
        sp.save_every = max(1, (self.steps+self.frames-2)//(self.frames-1))
        config.absorber.enabled = self.absorber
        config.absorber.strength, config.absorber.width_frac = self.absorber_strength, self.absorber_width
        config.validate()
        if not np.isfinite(self.steps*iv.dt):
            raise ValueError("Den fysiske sluttiden må være endelig.")
        cells = iv.nx * (iv.ny if self.dimension == 2 else 1)
        frame_count = 1 + self.steps//sp.save_every + int(self.steps % sp.save_every != 0)
        if cells > 1024*1024 or cells*frame_count*4 > 128*1024**2:
            raise ValueError("Appgrensen er 1 million punkter og 128 MiB lagrede bilder. Reduser rutenett eller bilder.")
        return config


def boundary_details(config, mask):
    iv = config.initial_values
    sine = config.dimension == 2 and mask is not None
    result = {"outer": "Dirichlet" if config.dimension == 1 or sine else "Periodic"}
    if result["outer"] == "Dirichlet":
        result["x_zero_nodes"] = [iv.x_min-iv.dx, iv.x_max+(iv.dx if config.dimension == 1 else 0)]
        if config.dimension == 2:
            result["y_zero_nodes"] = [iv.y_min-iv.dy, iv.y_max]
    if sine:
        blocked = np.flatnonzero(np.any(mask, axis=0))
        result["wall_faces"] = iv.x_grid[blocked[[0, -1]]].tolist()
        allowed = ~mask[:, blocked[len(blocked)//2]]
        edges = np.flatnonzero(np.diff(np.r_[False, allowed, False]))
        # If an opening reaches the outer box, its boundary is a ghost node.
        bounds = [[iv.y_grid[start-1] if start else iv.y_min-iv.dy,
                   iv.y_grid[stop] if stop < iv.ny else iv.y_max]
                  for start, stop in edges.reshape(-1, 2)]
        result["opening_zero_nodes"] = bounds
        result["opening_widths"] = [hi-lo for lo, hi in bounds]
    return result


@dataclass
class RunData:
    experiment: Experiment
    densities: np.ndarray
    summary: dict

    @property
    def times(self):
        return np.array(self.summary["times"])

    def metadata(self):
        return {"schema_version": 1, "experiment": asdict(self.experiment),
                "result": self.summary, "storage": "float32 densities; phase not stored"}

    def configuration_json(self):
        return json.dumps(self.metadata(), indent=2, ensure_ascii=False)


def calculate(experiment):
    config = experiment.configuration()
    mask, potential = get_barrier_mask(config), get_potential(config)
    result = simulate(get_wave_packet(config), potential, config, mask)
    summary = report(result, config)
    summary.update(dx=config.initial_values.dx, boundaries=boundary_details(config, mask),
                   python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__)
    if config.dimension == 2:
        summary["dy"] = config.initial_values.dy
    return RunData(experiment, np.stack(result.frames), summary)


def write_result(run, path):
    np.savez_compressed(path, densities=run.densities, metadata=run.configuration_json())


def read_result(path):
    with np.load(path, allow_pickle=False) as data:
        payload = json.loads(str(data["metadata"]))
        return RunData(Experiment(**payload["experiment"]), data["densities"].copy(), payload["result"])


def frame_png(run, frame, vmax=None):
    config = run.experiment.configuration()
    iv = config.initial_values
    density = run.densities[frame]
    fig = Figure(figsize=(7, 4.3), layout="constrained")
    ax = fig.subplots()
    if config.dimension == 1:
        ax.plot(iv.x_grid, density, color="#2c6e8f")
        ax.set(xlabel="x", ylabel="Probability density")
        potential = get_potential(config)
        if np.ptp(potential):
            twin = ax.twinx()
            twin.plot(iv.x_grid, potential, color="#d49336", alpha=0.5)
            twin.set_ylabel("V")
    else:
        extent = (iv.x_min-iv.dx/2, iv.x_max-iv.dx/2, iv.y_min-iv.dy/2, iv.y_max-iv.dy/2)
        if vmax is None:
            # One scale for the whole run, so scrubbing does not rescale intensity.
            samples = run.densities.ravel()[::max(1, run.densities.size//150000)]
            vmax = max(float(np.percentile(samples, 99.5)), float(np.max(run.densities))*0.01, 1e-12)
        image = ax.imshow(density, extent=extent, origin="lower", cmap="inferno", vmin=0, vmax=vmax)
        mask = get_barrier_mask(config)
        x, y = np.meshgrid(iv.x_grid, iv.y_grid)
        if mask is not None:
            ax.contour(x, y, mask.astype(float), levels=[0.5], colors="white", linewidths=0.7)
        else:
            potential = get_potential(config)
            if np.ptp(potential):
                ax.contour(x, y, potential, levels=[float((potential.max()+potential.min())/2)], colors="white")
        fig.colorbar(image, ax=ax, label="Probability density")
        ax.set(xlabel="x", ylabel="y")
    ax.set_title(f"t = {run.times[frame]:.5g}   P = {run.summary['probability'][frame]:.6f}")
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120)
    return buffer.getvalue()
