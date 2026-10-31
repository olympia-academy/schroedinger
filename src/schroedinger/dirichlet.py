"""Unitary directional sine propagation on the complement of a wall mask.

Each grid line is split at excluded cells. DST-I evolves each connected
interval with zero Dirichlet values at its two neighbouring boundary nodes.
No propagation interval crosses a wall, and no amplitude is deleted per step.
The x/y operators are composed symmetrically (second order in time).
"""
import numpy as np
from scipy.fft import dst, idst


class Direction:
    def __init__(self, mask, axis, spacing, duration, hbar, mass):
        self.axis = axis
        lines = mask if axis == 1 else mask.T
        patterns, membership = np.unique(lines, axis=0, return_inverse=True)
        self.blocks = []
        for label, pattern in enumerate(patterns):
            rows = np.flatnonzero(membership == label)
            edges = np.flatnonzero(np.diff(np.r_[False, ~pattern, False]))
            for start, stop in edges.reshape(-1, 2):
                length = stop - start
                k = np.pi * np.arange(1, length + 1) / ((length + 1) * spacing)
                phase = np.exp(-1j * hbar * k*k * duration / (2 * mass))
                self.blocks.append((rows, int(start), int(stop), phase))

    def step(self, psi):
        view = psi if self.axis == 1 else psi.T
        for rows, start, stop, phase in self.blocks:
            block = view[rows, start:stop]
            transformed = dst(block, type=1, axis=-1, norm="ortho")
            view[rows, start:stop] = idst(
                transformed * phase, type=1, axis=-1, norm="ortho")
        return psi


class DirichletKinetic:
    def __init__(self, mask, config):
        iv, c = config.initial_values, config.constants
        self.x_half = Direction(mask, 1, iv.dx, iv.dt/2, c.h_bar, c.mass)
        self.y_full = Direction(mask, 0, iv.dy, iv.dt, c.h_bar, c.mass)

    def step(self, psi):
        self.x_half.step(psi)
        self.y_full.step(psi)
        self.x_half.step(psi)
        return psi
