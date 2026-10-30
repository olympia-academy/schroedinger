# Schrödinger 2D

Two-dimensional time-dependent Schrödinger equation, solved with the
**split-step Fourier method** and animated as a `|ψ|²` heatmap.

The headline scenario is the **double slit through a true infinite barrier**:
the wall has `V = +∞` everywhere except at the two slit openings, so there
is *zero* tunneling through the wall — only the slits let probability
through.

This project is the 2D extension of the 1D project in `../1d`,
which uses RK4 + finite differences to demonstrate tunneling. The 2D solver
switches to FFT-based propagation because RK4 with a 2D Laplacian on a fine
grid is prohibitively slow and has tight stability constraints.

## Run

```bash
python main.py
```

Dependencies are listed in `requirements.txt` in the repository root
(`numpy`, `matplotlib` and `tqdm`; the last one is optional here).

## Scenarios

Set via `config.update("constants", potential_type=...)`. The default in
`main.py` is a plane wave hitting the double slit.

| `potential_type` | barrier model              | typical use                |
|------------------|----------------------------|----------------------------|
| `double_slit`    | **infinite** wall + 2 slits | the headline demo          |
| `single_slit`    | **infinite** wall + 1 slit  | comparison with 2-slit     |
| `wall`           | finite-V barrier            | 2D tunneling demo          |
| `free`           | V ≡ 0                       | free-particle sanity check |

`double_slit` and `single_slit` enforce `V = +∞` inside the wall via a
Dirichlet hard-wall mask (ψ ≡ 0 in those cells, every step). The `wall`
case keeps a finite `potential_strength` so a small fraction of the wave
tunnels through — handy as a 2D extension of the 1D tunneling demo. The
default V₀ = 22 is about 1.1 times the kinetic energy and lets roughly 4 %
of a Gaussian packet through. Transmission falls off exponentially with
√(V₀ − E), so V₀ = 200 already gives practically none.

## Initial wave functions

Set via `config.update("initial_values", wave_type=...)`:

| `wave_type`        | shape                                                     |
|--------------------|-----------------------------------------------------------|
| `gaussian_packet`  | 2D Gaussian, independent `sigma_x` and `sigma_y`          |
| `plane_wave`       | wave train: uniform in y, super-Gaussian envelope in x    |

Useful knobs (all on `config.initial_values`):

- `initial_position` — `(x0, y0)` of the packet centre
- `initial_momentum` — `(px, py)` momentum vector
- `sigma_x`, `sigma_y` — Gaussian widths (independent → make any size or
  shape). As in the 1D project, ψ ∝ exp(−((x − x₀)/σₓ)²), so the standard
  deviation of |ψ|² is σₓ/2.
- `plane_wave_envelope_width` — width of the super-Gaussian x-envelope; very
  large values approximate a true uniform plane wave

## Layout

```
2d/
├── config.py                # grid, barrier geometry, wave parameters
├── main.py                  # entry point
├── functions/
│   ├── potential.py         # V(x,y) + Dirichlet barrier mask
│   └── wave_functions.py    # gaussian_packet | plane_wave
├── tools/
│   └── simulate.py          # split-step Fourier + sponge layer + hard wall
└── plot/
    └── animate.py           # |ψ|² heatmap with wall overlay
```

## Method

The time-dependent Schrödinger equation

$$ i\hbar\,\partial_t\psi = -\frac{\hbar^2}{2m}\nabla^2\psi + V\psi $$

is split with Strang splitting:

$$ \psi(t+\Delta t) \approx
   e^{-iV\Delta t/2\hbar}\,
   \mathcal{F}^{-1}\!\Big[
     e^{-i\hbar k^2 \Delta t / 2m}\,
     \mathcal{F}\!\big[e^{-iV\Delta t/2\hbar}\psi(t)\big]
   \Big]
$$

The kinetic and potential operators are each unitary, so the propagation
itself preserves the norm up to FFT round-off (no renormalisation inside the
loop). The two ingredients below are deliberately not unitary: the hard wall
and the sponge layer both remove probability, so the total norm decreases
once the wave reaches the wall or the edges of the box.

Two extra ingredients keep the simulation physically sensible:

* **Dirichlet hard wall** — for slit scenarios, ψ is forced to 0 inside the
  wall after every step. Mathematically this is V = +∞ in those cells, and
  it gives **zero tunneling** through the wall.
* **Sponge / absorbing layer** — a smooth sin² ramp damps ψ in the
  outermost ~10% of the box on each side. The bare split-step Fourier
  method is periodic (FFT), so without a sponge the packet would wrap
  around to the other side; the sponge approximates open boundaries by
  draining outgoing probability before it reinjects.
