"""Explicit, independent configuration objects with derived grid quantities."""
from copy import deepcopy
from dataclasses import dataclass, field
import numpy as np


@dataclass
class Constants:
    mass: float = 10.0
    h_bar: float = 1.0
    potential_strength: float = 25.0
    potential_type: str = "square_wall"


@dataclass
class Grid1D:
    initial_position: float = 0.0
    initial_position_uncertainty: float = 1.0
    initial_momentum: float = 20.0
    x_min: float = -10.0
    x_max: float = 10.0
    nx: int = 3000
    _dt: float | None = field(default=None, repr=False)

    @property
    def x_grid(self):
        return np.linspace(self.x_min, self.x_max, self.nx)

    @x_grid.setter
    def x_grid(self, values):
        values = np.asarray(values, dtype=float)
        if (values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all()
                or np.any(np.diff(values) <= 0)
                or not np.allclose(np.diff(values), values[1] - values[0])):
            raise ValueError("x_grid must be a finite, increasing uniform 1D grid")
        self.nx = len(values)
        self.x_min, self.x_max = float(values[0]), float(values[-1])

    @property
    def dx(self):
        return (self.x_max - self.x_min) / (self.nx - 1)

    @property
    def dt(self):
        return self.dx**2 if self._dt is None else self._dt

    @dt.setter
    def dt(self, value):
        self._dt = value


@dataclass
class Grid2D:
    nx: int = 512
    ny: int = 256
    x_min: float = -15.0
    x_max: float = 25.0
    y_min: float = -10.0
    y_max: float = 10.0
    wave_type: str = "gaussian_packet"
    initial_position: tuple = (-8.0, 0.0)
    initial_momentum: tuple = (20.0, 0.0)
    sigma_x: float = 1.0
    sigma_y: float = 1.0
    plane_wave_envelope_width: float = 4.0
    _dt: float | None = field(default=None, repr=False)

    @property
    def x_grid(self):
        return np.linspace(self.x_min, self.x_max, self.nx, endpoint=False)

    @property
    def y_grid(self):
        return np.linspace(self.y_min, self.y_max, self.ny, endpoint=False)

    @property
    def dx(self):
        return (self.x_max - self.x_min) / self.nx

    @property
    def dy(self):
        return (self.y_max - self.y_min) / self.ny

    @property
    def dt(self):
        return 0.5 * min(self.dx, self.dy) if self._dt is None else self._dt

    @dt.setter
    def dt(self, value):
        self._dt = value


@dataclass
class Barrier1D:
    a: float = -5.0
    b: float = 5.0
    d: float = 0.5
    n: int = 2
    omega: float = 1.0


@dataclass
class Barrier2D:
    barrier_x: float = 0.0
    barrier_thickness: float = 0.4
    slit_width: float = 0.6
    slit_separation: float = 3.0
    omega: float = 1.0


@dataclass
class Absorber:
    enabled: bool = True
    width_frac: float = 0.10
    strength: float = 30.0  # amplitude decay rate, inverse simulation time


@dataclass
class SimulationParams:
    steps: int = 800
    save_every: int = 4
    method: str = "auto"
    progress: bool = True
    store_density: bool = False


def _positive(name, value, allow_zero=False):
    if not np.isscalar(value) or not np.isfinite(value) or (value < 0 if allow_zero else value <= 0):
        raise ValueError(f"{name} must be finite and {'nonnegative' if allow_zero else 'positive'}")


def _integer(name, value, minimum):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


class Configuration:
    """update() is atomic; validate() also catches direct attribute changes."""
    def update(self, category, **kwargs):
        if category not in {"constants", "initial_values", "simulation_params", "barrier", "absorber"}:
            raise AttributeError(f"Config has no category '{category}'")
        candidate = deepcopy(self)
        target = getattr(candidate, category)
        for key, value in kwargs.items():
            if key.startswith("_") or not hasattr(target, key):
                raise AttributeError(f"'{category}' has no attribute '{key}'")
            setattr(target, key, value)
        candidate.validate()
        setattr(self, category, target)

    @property
    def cell_volume(self):
        iv = self.initial_values
        return iv.dx if self.dimension == 1 else iv.dx * iv.dy

    def validate(self):
        iv, c, sp = self.initial_values, self.constants, self.simulation_params
        _positive("mass", c.mass)
        _positive("h_bar", c.h_bar)
        if not np.isfinite(c.potential_strength):
            raise ValueError("potential_strength must be finite")
        _integer("nx", iv.nx, 2)
        if not np.isfinite([iv.x_min, iv.x_max]).all() or iv.x_max <= iv.x_min:
            raise ValueError("x_max must be greater than finite x_min")
        if self.dimension == 2:
            _integer("ny", iv.ny, 2)
            if not np.isfinite([iv.y_min, iv.y_max]).all() or iv.y_max <= iv.y_min:
                raise ValueError("y_max must be greater than finite y_min")
            if len(iv.initial_position) != 2 or len(iv.initial_momentum) != 2:
                raise ValueError("2D position and momentum need two components")
            if not np.isfinite([*iv.initial_position, *iv.initial_momentum]).all():
                raise ValueError("Initial position and momentum must be finite")
            for name in ("sigma_x", "sigma_y", "plane_wave_envelope_width"):
                _positive(name, getattr(iv, name))
            if iv.wave_type not in {"gaussian_packet", "plane_wave"}:
                raise ValueError(f"Unknown wave type: {iv.wave_type}")
            for name in ("barrier_thickness", "slit_width", "slit_separation"):
                _positive(name, getattr(self.barrier, name))
            if not np.isfinite(self.barrier.barrier_x):
                raise ValueError("barrier_x must be finite")
            if c.potential_type == "double_slit" and self.barrier.slit_separation <= self.barrier.slit_width:
                raise ValueError("Double-slit openings must not overlap")
            allowed = {"free", "wall", "single_slit", "double_slit", "harmonic"}
        else:
            if not np.isfinite([iv.initial_position, iv.initial_momentum]).all():
                raise ValueError("Initial position and momentum must be finite")
            _positive("initial_position_uncertainty", iv.initial_position_uncertainty)
            if not np.isfinite([self.barrier.a, self.barrier.b]).all() or self.barrier.a >= self.barrier.b:
                raise ValueError("Barrier boundaries must satisfy a < b")
            _positive("d", self.barrier.d)
            _integer("n", self.barrier.n, 1)
            allowed = {"free", "square_wall", "square_well", "power", "harmonic"}
        if c.potential_type not in allowed:
            raise ValueError(f"Unknown {self.dimension}D potential type: {c.potential_type}")
        _positive("omega", self.barrier.omega)
        _positive("dt", iv.dt)
        momentum = (iv.initial_momentum,) if self.dimension == 1 else iv.initial_momentum
        spacings = (iv.dx,) if self.dimension == 1 else (iv.dx, iv.dy)
        if any(abs(p) / c.h_bar >= np.pi / d for p, d in zip(momentum, spacings)):
            raise ValueError("Initial momentum exceeds the grid Nyquist limit; refine the grid or reduce momentum")
        _integer("steps", sp.steps, 0)
        _integer("save_every", sp.save_every, 1)
        methods = {"auto", "crank_nicolson", "rk4"} if self.dimension == 1 else {"auto"}
        if sp.method not in methods:
            raise ValueError(f"Unsupported integration method: {sp.method}")
        _positive("absorber strength", self.absorber.strength, allow_zero=True)
        if not np.isfinite(self.absorber.width_frac) or not 0 < self.absorber.width_frac < 0.5:
            raise ValueError("absorber width_frac must lie between 0 and 0.5")
        return self


@dataclass
class Config1D(Configuration):
    constants: Constants = field(default_factory=Constants)
    initial_values: Grid1D = field(default_factory=Grid1D)
    simulation_params: SimulationParams = field(default_factory=lambda: SimulationParams(200000, 2000))
    barrier: Barrier1D = field(default_factory=Barrier1D)
    absorber: Absorber = field(default_factory=lambda: Absorber(enabled=False))
    dimension: int = field(default=1, init=False)


@dataclass
class Config2D(Configuration):
    constants: Constants = field(default_factory=lambda: Constants(potential_strength=22.0, potential_type="double_slit"))
    initial_values: Grid2D = field(default_factory=Grid2D)
    simulation_params: SimulationParams = field(default_factory=SimulationParams)
    barrier: Barrier2D = field(default_factory=Barrier2D)
    absorber: Absorber = field(default_factory=Absorber)
    dimension: int = field(default=2, init=False)
