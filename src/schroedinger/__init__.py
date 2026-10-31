"""Numerical quantum-mechanics demonstrations for Akademie Olympia."""
from .config import Config1D, Config2D
from .states import get_wave_packet
from .potentials import get_potential, get_barrier_mask
from .solvers import simulate

__all__ = ["Config1D", "Config2D", "get_wave_packet", "get_potential",
           "get_barrier_mask", "simulate"]
