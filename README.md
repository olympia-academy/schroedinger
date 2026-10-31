# Schroedinger — Akademie Olympia

[English](README.md) | [Norsk bokmål](README.nb.md)

Interactive numerical quantum mechanics for physics, research and education.

Prefer an experiment panel in your browser? The optional
[local app](docs/APP.md) supports Windows, macOS and Linux (Python 3.11+):

```bash
python -m pip install -e ".[app]"
python -m schroedinger.app
```

Choose parameters, inspect saved frames, play two runs in sync, and export/reopen
complete results or experiment settings. The existing command-line interface is documented below.
Start with a preset in **Utforsk** (Explore), change one parameter at fixed
final time in **Sammenlikn** (Compare), or open **Avansert** (Advanced) for
the full controls. The app derives propagation steps from physical final time.
Play, pause, restart and change display speed for saved frames directly in
the browser, without per-frame server calls or re-running the simulation.
Seeking pauses playback at the chosen frame. New default runs save 91 frames;
the default playback speed is 12 frames/s.
The light display highlights weak patterns and keeps a shared color scale for
comparisons. Region probabilities, 2D density profiles and guided time-step/grid
checks help interpret results. See the [app guide](docs/APP.md) for their limits.

## Install

Python 3.10 or later:

```powershell
# Windows PowerShell, from the repository folder:
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -e ".[test]"
& '.\.venv\Scripts\python.exe' -m schroedinger
```

```bash
# Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
python -m schroedinger
```

The following examples use `python`; on Windows you can substitute
`& '.\.venv\Scripts\python.exe'` without activating the environment.
The default example is a 2D wave train passing through two slits.

![Corrected double-slit demo at t = 7.03125](docs/images/double-slit.png)

Reproduce this figure with `python -m schroedinger --headless --no-progress --snapshot-time 7 --output docs/images/double-slit.png`.
The [JSON report](docs/images/double-slit.json) records the configuration and actual saved time.

## Explore

```bash
python -m schroedinger --scenario free --wave gaussian_packet
python -m schroedinger --scenario single_slit
python -m schroedinger --scenario double_slit --slit-width 0.8 --slit-separation 3
python -m schroedinger --scenario wall --wave gaussian_packet --potential-strength 22
python -m schroedinger --dimension 1
python -m schroedinger --dimension 1 --scenario harmonic --x0 -2 --px 0 --omega 1
python -m schroedinger --help
```

Use **Pause / Play**, **Restart**, and the frame slider in each animation.
The title shows physical time and the probability remaining in the box.
Closing the window ends the program. Parameters are command-line options;
editing source files is unnecessary.

For output without opening a window:

```bash
python -m schroedinger --headless --output outputs/double-slit.png
python -m schroedinger --headless --snapshot-time 7 --output outputs/at-t7.png
```

This writes a selected-frame PNG and a JSON report containing the exact
configuration, saved times, probability, absorbed probability, solver and
snapshot memory. Slit demos automatically choose a post-crossing preview
(about t=7.2 for the defaults); other scenarios use mid-time. Use
`--snapshot-time` to choose a physical time explicitly. The closest saved
frame is exported, and its actual index and time are recorded in JSON.
The entire time history remains available through the Python
API. The 2D demo stores float32 densities (one quarter of the complex snapshot
storage); Python API calls retain complex states by default.

## Methods and boundaries

| Problem | Method | Outer boundary |
|---|---|---|
| 1D, real static potential | Crank–Nicolson, factored tridiagonal solve | Zero Dirichlet values at ghost nodes |
| 1D comparison mode | RK4 with a checked stability bound | Same Dirichlet boundary |
| 2D free or finite potential | Fourier Strang splitting | Periodic, with an optional edge absorber |
| 2D infinite slit walls | Directional sine-transform Strang splitting on connected intervals | Zero Dirichlet values at ghost nodes, optional absorber |

An infinite wall **excludes cells from propagation**. Each grid line is split
at wall cells, with a unitary sine propagator in each allowed interval.
The symmetric x/y splitting is second order in time. A closed wall cannot
transmit probability between its two sides. There is no per-step deletion of
wave amplitude at the wall.

An initial state overlapping wall cells is projected and normalized **once
before t=0**; a substantial overlap produces a warning and is recorded in the
result. Closed-system evolution is never renormalized inside the loop.

The separate absorber uses an amplitude decay rate `gamma(x,y)` per unit
simulation time. Symmetric factors `exp(-gamma*dt/2)` surround the propagator.
Probability removed by those factors is measured separately. Without the
absorber, unitary solvers conserve probability to round-off; RK4 can drift.

Grid coordinates represent sample nodes. Sine and 1D finite-difference
boundaries lie at neighbouring ghost nodes. Wall and slit geometry is
rasterized, so effective dimensions change slightly with grid refinement.

## Accuracy

The defaults are visualization settings, not a certified continuum solution.
Conservation of probability alone is not evidence of spatial or temporal
convergence. Check smaller time steps and finer grids separately, and compare
the same physical final time. For example, doubling steps when halving dt:

```bash
python -m schroedinger --nx 1024 --ny 512 --dt 0.01 --steps 1600 --save-every 8
python -m schroedinger --nx 1024 --ny 512 --dt 0.005 --steps 3200 --save-every 16
```

These two examples end at t=16. Increasing grid resolution or frame count
increases runtime and memory use. Packets must resolve their momentum on the
grid; parameters beyond the Nyquist limit are rejected. Sharp slit corners
and discontinuous finite potentials particularly need convergence checks.

A Gaussian has an energy distribution. Transmission through a finite barrier
can include both sub-barrier tunnelling and above-barrier scattering. The
default finite-wall demo therefore makes no claim of a universal transmission
percentage or a pure tunnelling fraction.

Units default to hbar = 1. Momentum phases use `exp(i p*x/hbar)` for any
positive hbar. The historical Gaussian convention is retained:
`psi ~ exp(-((x-x0)/sigma)^2)`, so the standard deviation of position is
`sigma/2`.

## Tests and collaboration

```bash
python -m pytest -q
```

Tests cover closed-wall reflection and no transmission; analytic box
eigenstates; free-packet motion and spreading; second-order time refinement;
Crank–Nicolson norm preservation; continuum finite-barrier transmission;
time-consistent absorption and probability accounting; configuration changes;
nonunit hbar; expectation values; plotting controls and CLI exports.

GitHub Actions runs the suite on Windows and Linux with Python 3.10 and 3.12
when the workflow is pushed. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Python API

```python
from schroedinger import Config2D, get_wave_packet, get_potential, simulate

config = Config2D()
config.update("constants", potential_type="free")
config.update("initial_values", nx=256, initial_momentum=(5.0, 0.0))
config.absorber.enabled = False
result = simulate(get_wave_packet(config), get_potential(config), config)
print(result.times, result.norms)
```

Configuration instances are independent. Grid spacings are derived from
grid bounds and sizes. Automatic dt updates with the grid; an explicitly set
dt stays fixed. `SimulationResult` behaves like a sequence of frames and also
stores times, norms and absorbed probability. Expectation values in
`schroedinger.diagnostics` use the correct cell volume and distinguish
pointwise fields from matrix operators.

The old `1d/main.py` and `2d/main.py` entry points remain usable after
installation, with the same CLI options. Their helper modules are compatibility
wrappers around the shared package in `src/schroedinger/`.

## Authors and origins

The original 1D project was co-authored by
[Dag-Morten Sjøstrøm (@dagmortensj)](https://github.com/dagmortensj) and
[Dag-Vidar Krogstad Bauer (@dagvidb)](https://github.com/dagvidb), based on
Benjamin J. Land's [Quantum mechanics simulation](https://ben.land/post/2022/03/09/quantum-mechanics-simulation/).
The original 2D extension was developed with an AI coding assistant. This
revision adds validated propagators, shared configuration, diagnostics,
playback controls and automated tests while retaining the original Git history.

## Original version

The unchanged starting point is preserved under the
[`original` tag](https://github.com/olympia-academy/schroedinger/tree/original),
pointing to commit `a082b015aec9e74634d2331f9bca0149fc52f8ca`.
It contains the original standalone 1D and 2D scripts and illustrations.
