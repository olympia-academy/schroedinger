"""Configuration for the 2D Schrödinger simulation.

Mirrors the structure of the 1D project's config.py but extends every grid /
initial-value to 2D and adds geometry parameters for the double-slit barrier.

Default scenario: a Gaussian wave packet moving in +x direction toward a
barrier at x = 0 with two horizontal slits centred symmetrically about y = 0.
"""

import numpy as np


class Constants:
    def __init__(self) -> None:
        # Mass and momentum match the sibling 1D project so the visual pace
        # of propagation and dispersion is the same. Group velocity v = p/m,
        # so with m=10 and px=20 the packet drifts at v=2 and disperses
        # slowly (rate ~ 1 / (2 m σ²)).
        self.mass = 10.0
        self.h_bar = 1.0
        # Used only by the 'wall' scenario (a finite-V barrier for tunneling
        # demos). The 'double_slit' and 'single_slit' scenarios are infinite
        # barriers enforced by a Dirichlet mask -- this number is ignored.
        # The kinetic energy is E = p^2 / 2m = 20, so V0 = 22 is about 1.1 E.
        # With the default wall thickness 0.4 a Gaussian packet then sends
        # roughly 4 % of its probability through. Much higher values give
        # practically zero transmission (V0 = 200 gives about exp(-48)).
        self.potential_strength = 22.0
        # Which scenario to build: 'double_slit', 'single_slit', 'wall', 'free'
        self.potential_type = 'double_slit'


class BarrierGeometry:
    """Parameters controlling the slit barrier."""

    def __init__(self) -> None:
        self.barrier_x = 0.0       # x-coordinate of the wall
        self.barrier_thickness = 0.4
        self.slit_width = 0.6      # vertical opening size of each slit
        self.slit_separation = 3.0 # centre-to-centre distance between slits


class InitialValues:
    def __init__(self) -> None:
        # Spatial grid -- choose powers of two for efficient FFT
        self.nx = 512
        self.ny = 256
        self.x_min, self.x_max = -15.0, 25.0
        self.y_min, self.y_max = -10.0, 10.0

        self.x_grid = np.linspace(self.x_min, self.x_max, self.nx, endpoint=False)
        self.y_grid = np.linspace(self.y_min, self.y_max, self.ny, endpoint=False)
        self.dx = self.x_grid[1] - self.x_grid[0]
        self.dy = self.y_grid[1] - self.y_grid[0]

        # Which initial wave function to build: 'gaussian_packet' or 'plane_wave'
        self.wave_type = 'gaussian_packet'

        # Initial wave-function parameters (shared by all wave_types).
        # Momentum matches the 1D project (p=20) so v = p/m = 2 — slow enough
        # to follow visually, and the de Broglie wavelength λ = 2π/p ≈ 0.31 is
        # several times smaller than the slit separation, giving clean fringes.
        self.initial_position = (-8.0, 0.0)        # (x0, y0)
        self.initial_momentum = (20.0, 0.0)        # (px, py)

        # Gaussian packet: separate x/y widths so you can stretch the packet
        # independently. Increase to make a bigger / less-localised packet.
        # Same convention as the 1D project: psi ~ exp(-((x - x0) / sigma_x)^2),
        # so the standard deviation of |psi|^2 along x is sigma_x / 2.
        self.sigma_x = 1.0
        self.sigma_y = 1.0

        # Plane wave: super-Gaussian envelope localised in x (uniform in y).
        # A larger envelope width approximates a true uniform plane wave more
        # closely; a smaller one looks like a finite wave train hitting the
        # slits and then trailing off.
        self.plane_wave_envelope_width = 4.0

        # Time step. Split-step Fourier is unconditionally stable, but smaller
        # dt → smaller Trotter splitting error. dt ~ dx is a comfortable choice.
        self.dt = 0.5 * min(self.dx, self.dy)


class SimulationParams:
    def __init__(self) -> None:
        # With v=2 and dx≈0.078, the packet crosses the box (≈40 units) in
        # ~510 steps. We integrate ~1.6× that to capture the whole life of
        # the packet (approach → impact → diffraction → absorbed at edge).
        self.steps = 800
        self.save_every = 4      # → ~200 frames


class Config:
    def __init__(self) -> None:
        self.constants = Constants()
        self.barrier = BarrierGeometry()
        self.initial_values = InitialValues()
        self.simulation_params = SimulationParams()

    def update(self, category, **kwargs):
        """Update parameters dynamically for a specific category.

        Example:
            config.update("simulation_params", steps=400, save_every=4)
        """
        if hasattr(self, category):
            category_obj = getattr(self, category)
            for key, value in kwargs.items():
                if hasattr(category_obj, key):
                    setattr(category_obj, key, value)
                else:
                    raise AttributeError(f"'{category}' has no attribute '{key}'")
        else:
            raise AttributeError(f"Config has no category '{category}'")


# Default instance other modules can import
default_config = Config()
