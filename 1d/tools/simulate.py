import numpy as np
from tqdm import tqdm
from config import default_config


def normalize(f, config=default_config):
    dx = config.initial_values.dx
    norm = np.sum(np.square(np.abs(f))) * dx
    return f / np.sqrt(norm)


def d_dx2(f, config=default_config):
    dx = config.initial_values.dx
    df_dx2 = -2*f
    df_dx2[1:] += f[:-1]
    df_dx2[:-1] += f[1:]
    return df_dx2/(dx**2)


def hamiltonian(phi, v=0, config=default_config):
    # Right-hand side of the Schrödinger equation: dpsi/dt = i*hbar/(2m) psi'' - i*V*psi/hbar
    m = config.constants.mass
    h_bar = config.constants.h_bar
    return 1j*h_bar/2/m * d_dx2(phi, config=config) - 1j*v*phi/h_bar


def rk4(phi, dt, v=0, config=default_config):
    k1 = hamiltonian(phi, v=v, config=config)
    k2 = hamiltonian(phi + dt / 2 * k1, v=v, config=config)
    k3 = hamiltonian(phi + dt / 2 * k2, v=v, config=config)
    k4 = hamiltonian(phi + dt * k3, v=v, config=config)
    return phi + dt/6*(k1+2*k2+2*k3+k4)


def simulate(psi, v=0, config=default_config):

    dt = config.initial_values.dt
    steps = config.simulation_params.steps
    save_every = config.simulation_params.save_every

    psi = normalize(psi, config=config)
    simulation_steps = [np.copy(psi)]
    for i in tqdm(range(steps)):

        psi = rk4(psi, dt, v=v, config=config)
        psi = normalize(psi, config=config)

        if (i + 1) % save_every == 0:
            simulation_steps.append(np.copy(psi))

    return simulation_steps
