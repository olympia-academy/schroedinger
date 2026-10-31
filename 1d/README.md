# Schrödinger 1D

Install from the repository root using `python -m pip install -e .`.
Run `python main.py` here, or `python -m schroedinger --dimension 1`.

The default Gaussian packet starts at x=-8 and meets the finite wall near x=5.
The default solver is norm-preserving Crank–Nicolson. RK4 is available using
`--method rk4`, with a stability check and no per-step renormalization.

The plot shows real and imaginary amplitudes, the actual probability density
`|psi|^2`, the configured potential and physical time. Pause, restart and
frame selection are available. Examples and numerical validation are documented
in the [main README](../README.md).

