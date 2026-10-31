# Schrödinger 2D

Install the package from the repository root with `python -m pip install -e .`.
Then run `python main.py` here, or `python -m schroedinger` from any folder.

Examples:

```bash
python main.py --scenario single_slit
python main.py --scenario double_slit --slit-width 0.8
python main.py --scenario wall --wave gaussian_packet
python main.py --scenario free --no-absorber
python main.py --headless --output outputs/example.png
```

Slit walls use unitary directional sine propagation on allowed grid intervals,
with Dirichlet boundary values. They no longer erase amplitude after each
Fourier step. Free and finite-potential cases retain Fourier Strang splitting.

The edge absorber is optional and has a fixed decay rate per unit time.
The animation displays remaining probability; the JSON report also records
absorbed probability. GUI runs store float32 densities to reduce snapshot
memory, and offer pause, restart and frame selection.

Slit geometry is rasterized. Refine space and time before interpreting
transmission or fringe positions quantitatively. A finite-barrier Gaussian
demo can include above-barrier components as well as tunnelling.

See the [main README](../README.md) for definitions, boundaries, convergence
examples and automated tests. [Norsk bokmål](../README.nb.md).
