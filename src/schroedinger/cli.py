"""Run reproducible scenarios without editing source files."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import numpy as np
from .config import Config1D, Config2D
from .states import get_wave_packet
from .potentials import get_potential, get_barrier_mask
from .solvers import simulate


def parser():
    p = argparse.ArgumentParser(description="Akademie Olympia: Schrodinger simulations")
    p.add_argument("--dimension", "-d", type=int, choices=(1, 2), default=2)
    p.add_argument("--scenario", help="2D: double_slit, single_slit, wall, free, harmonic; "
                   "1D: square_wall, square_well, power, harmonic, free")
    p.add_argument("--wave", choices=("gaussian_packet", "plane_wave"))
    p.add_argument("--steps", type=int)
    p.add_argument("--save-every", type=int)
    p.add_argument("--nx", type=int)
    p.add_argument("--ny", type=int)
    p.add_argument("--dt", type=float)
    p.add_argument("--mass", type=float)
    p.add_argument("--hbar", type=float)
    p.add_argument("--px", type=float)
    p.add_argument("--py", type=float)
    p.add_argument("--x0", type=float)
    p.add_argument("--y0", type=float)
    p.add_argument("--sigma-x", type=float)
    p.add_argument("--sigma-y", type=float)
    p.add_argument("--envelope-width", type=float, help="2D plane-wave train envelope width")
    p.add_argument("--barrier-x", type=float)
    p.add_argument("--thickness", type=float)
    p.add_argument("--slit-width", type=float)
    p.add_argument("--slit-separation", type=float)
    p.add_argument("--potential-strength", type=float)
    p.add_argument("--omega", type=float)
    p.add_argument("--method", choices=("auto", "crank_nicolson", "rk4"), default="auto")
    p.add_argument("--no-absorber", action="store_true")
    p.add_argument("--absorber-strength", type=float)
    p.add_argument("--absorber-width", type=float)
    p.add_argument("--no-progress", action="store_true")
    p.add_argument("--headless", action="store_true", help="Save a preview and JSON report instead of opening a window")
    p.add_argument("--output", type=Path, help="PNG destination (also writes a JSON sidecar)")
    p.add_argument("--snapshot-time", type=float,
                   help="Physical time for the PNG; selects the closest saved frame")
    return p


def configuration(args):
    config = Config1D() if args.dimension == 1 else Config2D()
    iv, c, sp, bg = config.initial_values, config.constants, config.simulation_params, config.barrier
    if args.dimension == 1:
        iv.initial_position = -8.0
        bg.a = -10.0
        c.potential_strength = 24.0
        if any(getattr(args, name) is not None for name in
               ("ny", "wave", "py", "y0", "sigma_y", "envelope_width", "barrier_x", "slit_width", "slit_separation")):
            raise ValueError("The supplied options require --dimension 2")
    else:
        iv.wave_type = "plane_wave"
        sp.store_density = True
    for attr, value in (("nx", args.nx), ("dt", args.dt)):
        if value is not None:
            setattr(iv, attr, value)
    if args.dimension == 2:
        for attr, value in (("ny", args.ny), ("wave_type", args.wave), ("sigma_x", args.sigma_x),
                            ("sigma_y", args.sigma_y), ("plane_wave_envelope_width", args.envelope_width)):
            if value is not None:
                setattr(iv, attr, value)
        iv.initial_position = (args.x0 if args.x0 is not None else iv.initial_position[0],
                               args.y0 if args.y0 is not None else iv.initial_position[1])
        iv.initial_momentum = (args.px if args.px is not None else iv.initial_momentum[0],
                               args.py if args.py is not None else iv.initial_momentum[1])
        for attr, value in (("barrier_x", args.barrier_x), ("barrier_thickness", args.thickness),
                            ("slit_width", args.slit_width), ("slit_separation", args.slit_separation)):
            if value is not None:
                setattr(bg, attr, value)
    else:
        for attr, value in (("initial_position", args.x0), ("initial_momentum", args.px),
                            ("initial_position_uncertainty", args.sigma_x)):
            if value is not None:
                setattr(iv, attr, value)
        if args.thickness is not None:
            bg.d = args.thickness
    for attr, value in (("mass", args.mass), ("h_bar", args.hbar),
                        ("potential_strength", args.potential_strength), ("potential_type", args.scenario)):
        if value is not None:
            setattr(c, attr, value)
    if args.omega is not None:
        bg.omega = args.omega
    for attr, value in (("steps", args.steps), ("save_every", args.save_every)):
        if value is not None:
            setattr(sp, attr, value)
    sp.method = args.method
    sp.progress = not args.no_progress
    if args.no_absorber:
        config.absorber.enabled = False
    if args.absorber_strength is not None:
        config.absorber.strength = args.absorber_strength
    if args.absorber_width is not None:
        config.absorber.width_frac = args.absorber_width
    return config.validate()


def report(result, config):
    return {
        "solver": result.solver,
        "config": asdict(config),
        "dt": config.initial_values.dt,
        "cell_volume": config.cell_volume,
        "frames": len(result),
        "frame_storage": "float32 density" if result.is_density else "complex128 wave function",
        "snapshot_bytes": sum(frame.nbytes for frame in result),
        "times": result.times.tolist(),
        "probability": result.norms.tolist(),
        "absorbed_probability": result.absorbed.tolist(),
        "max_probability_budget_error": float(np.max(np.abs(result.norms + result.absorbed - result.norms[0]))),
        "initial_projection_loss": result.initial_projection_loss,
    }


def snapshot_index(times, config, requested_time=None):
    """Pick a saved frame at a requested time or after the slit crossing.

    The automatic slit preview follows the incident packet centre a quarter
    of the way into the downstream region. Other scenarios use mid-time.
    This is a display heuristic; it does not change numerical evolution.
    """
    times = np.asarray(times)
    if requested_time is not None:
        if not np.isfinite(requested_time) or not times[0] <= requested_time <= times[-1]:
            raise ValueError(f"snapshot-time must be between {times[0]:g} and {times[-1]:g}")
        target = requested_time
    else:
        target = (times[0] + times[-1])/2
        if config.dimension == 2 and config.constants.potential_type in {"single_slit", "double_slit"}:
            iv = config.initial_values
            velocity = iv.initial_momentum[0] / config.constants.mass
            if velocity != 0:
                hit_time = (config.barrier.barrier_x - iv.initial_position[0]) / velocity
                if hit_time >= 0:
                    edge = iv.x_max if velocity > 0 else iv.x_min
                    screen = config.barrier.barrier_x + 0.25*(edge-config.barrier.barrier_x)
                    target = (screen-iv.initial_position[0]) / velocity
                    target = np.clip(target, times[0], times[-1])
    return int(np.argmin(np.abs(times-target)))


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    try:
        config = configuration(args)
        if args.snapshot_time is not None:
            if not (args.headless or args.output is not None):
                raise ValueError("--snapshot-time requires --headless or --output")
            snapshot_index([0, config.simulation_params.steps*config.initial_values.dt],
                           config, args.snapshot_time)
        psi = get_wave_packet(config)
        potential, mask = get_potential(config), get_barrier_mask(config)
        result = simulate(psi, potential, config, mask)
    except (ValueError, AttributeError) as exc:
        p.error(str(exc))
    print(f"Solver: {result.solver}; frames: {len(result)}; "
          f"P(initial)={result.norms[0]:.8f}; P(final)={result.norms[-1]:.8f}; "
          f"absorbed={result.absorbed[-1]:.8f}")
    if args.headless:
        import matplotlib
        matplotlib.use("Agg")
    from .visualization import animate
    animation = animate(result, config, potential, mask, show=False)
    if args.headless or args.output is not None:
        output = args.output or Path("outputs") / f"{args.dimension}d-{config.constants.potential_type}.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        frame = snapshot_index(result.times, config, args.snapshot_time)
        animation._fig.canvas.draw()
        animation._func(frame)
        animation._fig.savefig(output, dpi=140)
        summary = report(result, config)
        summary.update(snapshot_frame=frame, snapshot_time=float(result.times[frame]),
                       snapshot_requested_time=args.snapshot_time)
        output.with_suffix(".json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Saved {output} and {output.with_suffix('.json')}")
    import matplotlib.pyplot as plt
    if args.headless:
        plt.close(animation._fig)
    else:
        plt.show()
    return result


def entrypoint():
    main()


if __name__ == "__main__":
    main()
