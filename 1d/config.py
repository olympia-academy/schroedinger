import numpy as np


class Constants:
    def __init__(self) -> None:
        self.mass = 10
        self.h_bar = 1
        self.potential_strength = 25
        self.potential_type = 'square_wall'


class InitialValues:
    def __init__(self) -> None:
        self.initial_position = 0
        # Width of the packet psi ~ exp(-(x - x0)^2 / sigma^2). The standard
        # deviation of the position distribution |psi|^2 is sigma / 2.
        self.initial_position_uncertainty = 1
        self.initial_momentum = 20
        self.x_grid = np.linspace(-10, 10, 3000)
        self.dx = self.x_grid[1] - self.x_grid[0]
        self.dt = self.dx ** 2


class SimulationParams:
    def __init__(self) -> None:
        self.steps = 200000
        self.save_every = 2000


class Config:
    def __init__(self) -> None:
        self.constants = Constants()
        self.initial_values = InitialValues()
        self.simulation_params = SimulationParams()

    def update(self, category, **kwargs):
        """
        Update parameters dynamically for a specific category.
        Example usage:
            config.update("simulation", steps=2000, save_every=50)
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


# Initialize a default instance of Config
default_config = Config()