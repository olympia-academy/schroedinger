from copy import deepcopy
import numpy as np
import pytest
from schroedinger import get_wave_packet, get_potential, get_barrier_mask, simulate
from schroedinger.diagnostics import probability, normalize, expectation


def test_expectation_uses_volume_and_matrix_action(config2):
    psi = get_wave_packet(config2)
    assert expectation(psi, np.ones_like(psi), config2.cell_volume) == pytest.approx(1)
    state = np.array([1, 0, 0, 0], dtype=complex)
    assert expectation(state, np.ones((4, 4)), 1) == 1


@pytest.mark.parametrize("bad", [np.zeros(5), np.full(5, np.nan), np.full(5, np.inf)])
def test_invalid_wave_functions_are_rejected(bad):
    with pytest.raises(ValueError):
        normalize(bad, 0.1)


def test_free_gaussian_matches_analytic_motion_and_spreading(config2):
    c = config2
    result = simulate(get_wave_packet(c), 0, c)
    t = result.times[-1]
    iv = c.initial_values
    x, _ = np.meshgrid(iv.x_grid, iv.y_grid)
    mean = expectation(result[-1], x, c.cell_volume)
    variance = expectation(result[-1], (x-mean)**2, c.cell_volume)
    assert mean == pytest.approx(-3 + 2*t, abs=1e-6)
    assert variance == pytest.approx(0.25 + t*t, abs=2e-6)
    assert np.max(abs(result.norms-1)) < 2e-12


@pytest.mark.parametrize("has_internal_wall", [False, True])
def test_dirichlet_box_eigenstate_has_exact_phase_and_no_transmission(config2, has_internal_wall):
    c = config2
    iv = c.initial_values
    mask = np.zeros((iv.ny, iv.nx), dtype=bool)
    length_x = iv.nx
    if has_internal_wall:
        length_x = iv.nx//2
        mask[:, length_x] = True
    psi = np.zeros(mask.shape, dtype=complex)
    psi[:, :length_x] = (
        np.sin(np.pi*np.arange(1, iv.ny+1)/(iv.ny+1))[:, None] *
        np.sin(np.pi*np.arange(1, length_x+1)/(length_x+1))[None, :])
    psi = normalize(psi, c.cell_volume)
    result = simulate(psi, 0, c, mask)
    energy = c.constants.h_bar**2/(2*c.constants.mass) * (
        (np.pi/((length_x+1)*iv.dx))**2 + (np.pi/((iv.ny+1)*iv.dy))**2)
    exact = psi*np.exp(-1j*energy*result.times[-1]/c.constants.h_bar)
    assert np.linalg.norm(result[-1]-exact)/np.linalg.norm(exact) < 3e-12
    assert np.max(abs(result.norms-1)) < 3e-12
    if has_internal_wall:
        assert np.count_nonzero(result[-1][:, length_x:]) == 0


@pytest.mark.parametrize("subdivision", [1, 2, 4])
def test_closed_wall_reflects_without_losing_probability(config2, subdivision):
    c = config2
    c.initial_values.dt /= subdivision
    c.simulation_params.steps = 150*subdivision
    c.simulation_params.save_every = c.simulation_params.steps
    iv = c.initial_values
    x, _ = np.meshgrid(iv.x_grid, iv.y_grid)
    mask = np.abs(x) <= iv.dx/2
    psi = get_wave_packet(c)
    psi[x >= 0] = 0  # strictly incident from the left; no initial right-hand tail
    result = simulate(psi, 0, c, mask)
    assert np.max(abs(result.norms-1)) < 3e-11
    assert probability(result[-1][x > iv.dx/2], c.cell_volume) == 0
    assert np.count_nonzero(result[-1][mask]) == 0
    assert result.absorbed[-1] == 0


def test_reflected_packet_matches_continuum_method_of_images(config2):
    c = config2
    iv = c.initial_values
    iv.nx = iv.ny = 160
    iv.x_min = iv.y_min = -20
    iv.x_max = iv.y_max = 20
    c.simulation_params.steps = 100
    c.simulation_params.save_every = 100
    x, y = np.meshgrid(iv.x_grid, iv.y_grid)
    mask = x == 0

    def gaussian(coord, center, momentum, time):
        spread = 1 + 2j*time  # sigma = hbar = mass = 1
        return (np.exp(-((coord-center-momentum*time)**2)/spread)
                * np.exp(1j*momentum*coord - 0.5j*momentum**2*time)/np.sqrt(spread))

    def exact(time):
        state = ((gaussian(x, -3, 2, time)-gaussian(-x, -3, 2, time))
                 * gaussian(y, 0, 0, time))
        state[x >= 0] = 0
        return normalize(state, c.cell_volume)

    result = simulate(exact(0), 0, c, mask)
    reference = exact(result.times[-1])
    assert np.linalg.norm(result[-1]-reference)/np.linalg.norm(reference) < 2e-6


def test_slit_time_refinement_is_second_order(config2):
    c = config2
    c.constants.potential_type = "single_slit"
    c.barrier.slit_width = 1.0
    c.initial_values.initial_position = (-1.2, 0)
    c.initial_values.sigma_x = 0.8
    mask = get_barrier_mask(c)
    psi = get_wave_packet(c)
    psi[mask] = 0
    finals = []
    for dt in (0.002, 0.001, 0.000125):
        cfg = deepcopy(c)
        cfg.initial_values.dt = dt
        cfg.simulation_params.steps = round(0.1/dt)
        cfg.simulation_params.save_every = cfg.simulation_params.steps
        finals.append(simulate(psi, 0, cfg, mask)[-1])
    errors = [np.linalg.norm(state-finals[-1]) for state in finals[:2]]
    assert 3.4 < errors[0]/errors[1] < 4.8


def test_absorption_has_a_time_independent_rate_and_balances_probability(config1):
    c = config1
    c.initial_values.nx = 128
    c.initial_values.initial_momentum = 0
    c.initial_values.initial_position = -9
    c.initial_values.initial_position_uncertainty = 0.7
    c.constants.mass = 1e12
    c.absorber.enabled = True
    c.absorber.strength = 3
    c.absorber.width_frac = 0.2
    norms = []
    for dt, steps in ((0.03, 10), (0.015, 20)):
        cfg = deepcopy(c)
        cfg.initial_values.dt = dt
        cfg.simulation_params.steps = steps
        result = simulate(get_wave_packet(cfg), 0, cfg)
        assert 0 < result.norms[-1] < 1
        assert np.max(abs(result.norms+result.absorbed-1)) < 2e-12
        norms.append(result.norms[-1])
    assert abs(norms[0]-norms[1]) < 2e-12


def test_crank_nicolson_preserves_norm_and_box_eigenstate(config1):
    c = config1
    iv = c.initial_values
    iv.nx = 128
    iv.x_min, iv.x_max = 0, 10
    iv.dt = 0.05
    iv.initial_momentum = 0
    c.simulation_params.steps = 200
    psi = normalize(np.sin(np.pi*np.arange(1, iv.nx+1)/(iv.nx+1)), c.cell_volume)
    result = simulate(psi, 0, c)
    energy = np.pi**2 / (2*((iv.nx+1)*iv.dx)**2)
    exact = psi*np.exp(-1j*energy*result.times[-1])
    assert np.linalg.norm(result[-1]-exact)/np.linalg.norm(exact) < 1e-4
    assert np.max(abs(result.norms-1)) < 2e-12


def test_rk4_does_not_hide_norm_error_and_rejects_unstable_steps(config1):
    c = config1
    c.simulation_params.method = "rk4"
    c.simulation_params.steps = 1
    c.initial_values.nx = 32
    c.initial_values.initial_momentum = 0
    c.initial_values.dt = 0.3
    psi = np.sin(31*np.pi*np.arange(1, 33)/33)
    result = simulate(psi, 0, c)
    assert result.norms[-1] < 0.99
    c.initial_values.dt = 10
    with pytest.raises(ValueError, match="stability"):
        simulate(psi, 0, c)


def test_finite_barrier_transmission_against_analytic_scattering(config1):
    c = config1
    iv = c.initial_values
    iv.nx = 2049
    iv.x_min, iv.x_max = -20, 20
    iv.initial_position = -10
    iv.initial_momentum = 4
    iv.initial_position_uncertainty = 3
    iv.dt = 0.002
    c.simulation_params.steps = 3000
    c.simulation_params.save_every = 3000
    x = iv.x_grid
    wall = np.abs(x) <= 0.5
    height = 12.0
    width = wall.sum()*iv.dx
    result = simulate(get_wave_packet(c), height*wall, c)
    measured = probability(result[-1][x > 0.5], c.cell_volume)
    p = np.linspace(0.001, 8.0, 30001)
    e = p*p/2
    weights = np.exp(-0.5*((p-4)*3)**2)
    transmission = np.empty_like(p)
    below = e < height
    kappa = np.sqrt(2*(height-e[below]))
    q = np.sqrt(2*(e[~below]-height))
    transmission[below] = 1/(1+height**2*np.sinh(kappa*width)**2/(4*e[below]*(height-e[below])))
    transmission[~below] = 1/(1+height**2*np.sin(q*width)**2/(4*e[~below]*(e[~below]-height)))
    reference = float(np.sum(weights*transmission)/np.sum(weights))
    assert measured == pytest.approx(reference, rel=0.03)


def test_result_saves_final_time_and_density_without_mutating_inputs(config2):
    c = config2
    c.simulation_params.steps = 7
    c.simulation_params.save_every = 3
    c.simulation_params.store_density = True
    psi = get_wave_packet(c)
    original = psi.copy()
    result = simulate(psi, 0, c)
    assert np.array_equal(psi, original)
    assert np.allclose(result.times, [0, 0.06, 0.12, 0.14])
    assert result[0].dtype == np.float32
    assert result[0].nbytes == original.nbytes//4
    assert np.allclose(result.density(0), abs(original)**2)


@pytest.mark.parametrize("case", ["shape", "potential", "mask"])
def test_invalid_solver_arrays(config2, case):
    psi = get_wave_packet(config2)
    with pytest.raises(ValueError):
        if case == "shape":
            simulate(psi[:, :-1], 0, config2)
        elif case == "potential":
            simulate(psi, complex(1, 1), config2)
        else:
            simulate(psi, 0, config2, np.zeros(2))
