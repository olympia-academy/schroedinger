"""Entry point for the 2D Schrödinger simulation.

Default scenario: a plane wave train (uniform in y, localised in x) hitting a
vertical wall with two slits (true infinite barrier — no tunneling through the
wall, only the slit openings let probability through).

Toggles you'll likely want to play with:

    config.update("constants",      potential_type='double_slit')
        # or 'single_slit' (also infinite barrier),
        # or 'wall' (finite-V tunneling demo, uses potential_strength),
        # or 'free' (no barrier).

    config.update("initial_values", wave_type='gaussian_packet')
        # or 'plane_wave' (a wave train, uniform in y, localised in x).

    config.update("initial_values", sigma_x=2.0, sigma_y=4.0)
        # bigger / elliptical Gaussian packet.

    config.update("initial_values", plane_wave_envelope_width=10.0)
        # wider envelope → closer to a true uniform plane wave.
"""

from config import Config
from functions.potential import get_barrier_mask, get_potential
from functions.wave_functions import get_wave_packet
from plot.animate import animate
from tools.simulate import simulate


def main():
    config = Config()

    # Scenario selection -- 'double_slit' is the headline demo
    config.update("constants", potential_type='double_slit')
    config.update("initial_values", wave_type='plane_wave')

    psi0 = get_wave_packet(config=config)
    V = get_potential(config=config)
    mask = get_barrier_mask(config=config)

    snapshots = simulate(psi=psi0, v=V, config=config, barrier_mask=mask)

    animate(simulation=snapshots, potential=V,
            barrier_mask=mask, config=config)


if __name__ == '__main__':
    main()
