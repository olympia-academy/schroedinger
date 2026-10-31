# Numerical validation

## Regression against the original closed wall

The original repository snapshot is `a082b015aec9e74634d2331f9bca0149fc52f8ca`.
A 512 x 256 grid, mass 10, hbar 1, momentum (20,0), a Gaussian initially
near (-8,0), a closed vertical slab of thickness 0.4 and **no edge absorber**
were evolved to t=6.25.

| dt | Original remaining probability | Revised remaining probability |
|---|---:|---:|
| 0.0390625 | 0.3119516744 | 0.9999999999996 |
| 0.01953125 | 0.5589491284 | 0.9999999999993 |
| 0.009765625 | 0.7476495946 | 0.9999999999986 |

The revised incident state is strictly zero on and to the right of the wall.
The original Gaussian's right-hand tail at t=0 is negligible at this position.
The revised propagator has exactly zero transmission to the initially empty
side; the original showed approximately 0.0002 of the initial probability there.

This establishes probability conservation and separation of the two sides.
It does not establish arbitrary slit geometries' continuum accuracy.

## Automated reference problems

Run `python -m pytest -q`.

The suite includes analytic free Gaussian motion and spreading, exact
Dirichlet box eigenstates, closed-wall reflection, second-order time
refinement at a slit, 1D box evolution, and continuum rectangular-barrier
transmission integrated over the incident Gaussian momentum distribution.

Absorption is checked using an effectively stationary packet and two time
subdivisions. Its final probability agrees, and the probability plus the
measured absorber loss is one to numerical tolerance. Matrix and pointwise
expectation operators, nonunit hbar, invalid parameters, saved time stamps,
CLI exports and playback controls also have regression coverage.

## End-to-end default runs

Both revised default entry points were executed and rendered locally.
The revised 2D demo stores 201 density frames occupying 105,381,888 bytes,
versus 421,527,552 bytes for the original complex snapshots. Its measured
maximum probability-budget error was approximately 3.8e-13.

These figures were measured on Windows / Python 3.12.10 with NumPy 2.5.4,
SciPy 1.18.1 and Matplotlib 3.11.2. GitHub Actions is configured for Windows
and Linux on Python 3.10 and 3.12; those hosted jobs run after publication.

## Interpretation limits

Local interactive Windows testing found desktop stuttering when concurrent
full-size GUI simulations were launched. Responsiveness returned after the
processes stopped. Available RAM was approximately 14–15 GiB out of 32 GiB;
a short CPU sample did not establish sustained CPU saturation or a root cause.
The user subsequently tried and accepted the low-load launcher: one simulation,
below-normal Windows priority, one logical CPU, smaller display, 80 ms playback,
and playback paused initially. `tools/view_low_load.py` reproduces that setup
without changing the corrected experiment's physical parameters.

- Hard-wall kinetic evolution uses sine transforms on connected grid intervals.
  Ghost-node Dirichlet boundaries and rasterized geometry are part of the model.
- Directional splitting at corners has finite time error. Refine dt and grid
  spacing before quantitative slit comparisons.
- Free/finite-potential Fourier cases are periodic without the absorber.
  Hard-wall cases have Dirichlet outer boundaries without the absorber.
- Multiplicative boundary absorption can still reflect some outgoing waves;
  width and decay rate require convergence checks for a given packet.
- Finite-barrier transmission can include above-barrier components.
- Float32 density snapshots are for display; norms are measured from the
  complex128 state before conversion. Retain complex frames for phase-sensitive analysis.
