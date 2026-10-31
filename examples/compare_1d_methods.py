"""Et lite, selvstendig 1D-eksempel: samme Hamilton-operator, to tidsmetoder.

Kjør fra repoet: python examples/compare_1d_methods.py --method both
Ingen vinduer åpnes. Figuren og tallene skrives til outputs/teaching/.
Dette er undervisningskode; produksjonsløseren ligger i src/schroedinger/.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import solve_banded


def compare(method="both", dt=0.002, output=Path("outputs/teaching")):
    # Naturlige enheter: hbar = masse = 1. Fri partikkel: V = 0.
    # Punktene er INNE i boksen; psi = 0 ved nabopunktene utenfor rutenettet.
    x = np.linspace(-10, 10, 201)
    dx = x[1] - x[0]
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and positive")
    # Begge metoder stopper ved samme fysiske tid, T = 1.
    steps = int(np.ceil(1 / dt))
    dt = 1 / steps
    if method in {"both", "rk4"} and dt * 2 / dx**2 > np.sqrt(8):
        raise ValueError("RK4 is unstable here: reduce dt")

    # exp(i*p*x/hbar) gir p = 2. Breddekonvensjonen er sigma = 1.
    initial = np.exp(2j*x) * np.exp(-(x+3)**2)
    initial /= np.sqrt(np.sum(abs(initial)**2)*dx)

    def hamiltonian(psi):
        # H psi = -hbar^2/(2m) * psi''. Ingen periodisk np.roll her!
        laplacian = -2*psi.copy()
        laplacian[1:] += psi[:-1]
        laplacian[:-1] += psi[1:]
        return -0.5*laplacian/dx**2

    def rhs(psi):
        # i*hbar*dpsi/dt = H psi, altså dpsi/dt = -i*H psi.
        return -1j*hamiltonian(psi)

    # Crank-Nicolson: (I+i*dt*H/2) psi_ny = (I-i*dt*H/2) psi.
    # solve_banded løser et tridiagonalt system. Produksjonskoden
    # faktoriserer venstresiden én gang for å spare arbeid.
    left = np.zeros((3, len(x)), dtype=complex)
    left[1] = 1 + 0.5j*dt/dx**2
    left[0, 1:] = left[2, :-1] = -0.25j*dt/dx**2

    methods = ("crank_nicolson", "rk4") if method == "both" else (method,)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots()
    ax.plot(x, abs(initial)**2, "--", label="Initial, t=0")
    report = {"dt": dt, "steps": steps, "time": 1.0, "dx": dx,
              "boundary": "zero Dirichlet at x=-10.1 and x=10.1", "methods": {}}
    for name in methods:
        psi = initial.copy()
        for _ in range(steps):
            if name == "crank_nicolson":
                right = psi - 0.5j*dt*hamiltonian(psi)
                psi = solve_banded((1, 1), left, right)
            else:
                # RK4 vurderer helningen fire ganger innenfor hvert steg.
                k1 = rhs(psi)
                k2 = rhs(psi + dt*k1/2)
                k3 = rhs(psi + dt*k2/2)
                k4 = rhs(psi + dt*k3)
                psi = psi + dt*(k1 + 2*k2 + 2*k3 + k4)/6
            # Ingen renormalisering: et eventuelt normtap skal være synlig.
        density = abs(psi)**2
        norm = float(density.sum()*dx)
        mean = float(np.sum(x*density)*dx/norm)
        report["methods"][name] = {"probability": norm, "mean_x": mean}
        ax.plot(x, density, label=name)
    # Kontinuumreferanse: <x>(1) = -3 + p*T/m = -1.
    # Avvik skyldes både rom- og tidsdiskretisering, samt endelig boks.
    report["continuum_mean_x"] = -1.0
    ax.set(xlabel="x", ylabel="Probability density", title="Free packet, t=1")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "methods.png", dpi=140)
    plt.close(fig)
    (output / "methods.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=("both", "crank_nicolson", "rk4"), default="both")
    parser.add_argument("--dt", type=float, default=0.002)
    parser.add_argument("--output", type=Path, default=Path("outputs/teaching"))
    args = parser.parse_args()
    compare(args.method, args.dt, args.output)
