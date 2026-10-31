"""Probability and expectation values with the correct integration measure."""
import numpy as np


def probability(psi, cell_volume):
    return float(np.sum(np.abs(psi)**2) * cell_volume)


def normalize(psi, cell_volume):
    psi = np.asarray(psi, dtype=complex)
    norm = probability(psi, cell_volume)
    if not np.isfinite(psi).all() or not np.isfinite(norm) or norm <= 0:
        raise ValueError("Wave function must have a finite, positive norm")
    return psi / np.sqrt(norm)


def expectation(psi, operator, cell_volume):
    """Return <A>, normalized by the current norm even in an absorbing box.

    A callable applies an operator; a grid-shaped array multiplies pointwise;
    a (psi.size, psi.size) matrix acts on the flattened state.
    """
    psi = np.asarray(psi, dtype=complex)
    norm = probability(psi, cell_volume)
    if not np.isfinite(psi).all() or norm <= 0 or not np.isfinite(norm):
        raise ValueError("Expectation needs a finite state with positive norm")
    if callable(operator):
        applied = np.asarray(operator(psi))
    else:
        op = np.asarray(operator)
        if op.shape == psi.shape or op.ndim == 0:
            applied = op * psi
        elif op.shape == (psi.size, psi.size):
            applied = (op @ psi.ravel()).reshape(psi.shape)
        else:
            raise ValueError("Operator must be scalar, grid-shaped, a matrix, or callable")
    if applied.shape != psi.shape or not np.isfinite(applied).all():
        raise ValueError("Operator produced an invalid state")
    value = np.vdot(psi, applied) * cell_volume / norm
    return np.real_if_close(value).item()
