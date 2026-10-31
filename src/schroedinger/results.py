"""Saved frames plus physical times and probability accounting."""
from collections.abc import Sequence
from dataclasses import dataclass
import numpy as np


@dataclass
class SimulationResult(Sequence):
    frames: list
    times: np.ndarray
    norms: np.ndarray
    absorbed: np.ndarray
    is_density: bool
    solver: str
    initial_projection_loss: float = 0.0

    def __len__(self):
        return len(self.frames)

    def __getitem__(self, item):
        return self.frames[item]

    def density(self, index):
        return self.frames[index] if self.is_density else np.abs(self.frames[index])**2
