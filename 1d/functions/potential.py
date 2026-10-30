from config import default_config
import numpy as np


def get_potential(config=default_config, **kwargs):

    x = config.initial_values.x_grid
    v0 = config.constants.potential_strength
    kind = config.constants.potential_type

    if kind == "square_well":
        a, b = kwargs.get('a', -5), kwargs.get('b', 5)
        return np.where((x > a) & (x < b), 0, v0)

    elif kind == "square_wall":
        a, b, d = kwargs.get('a', -5), kwargs.get('b', 5), kwargs.get('d', 0.5)
        return np.where(((a - d <= x) & (x <= a)) | ((b <= x) & (x <= b + d)), v0, 0)

    elif kind == "power":
        n = kwargs.get('n', 2)
        return v0 * x ** n
    else:
        raise ValueError(f"Unknown potential type: {kind}")


