"""Position moments and the continuum reference for an unchirped free Gaussian."""
import numpy as np
from scipy.special import ndtr


def position_moments(densities, x):
    """Conditional mean/std from 1D density snapshots using the solver's dx sum.

    Each snapshot is normalized by its own probability. Zero probability gives
    undefined (NaN) moments. This does not modify or renormalize stored data.
    """
    densities, x = np.asarray(densities), np.asarray(x, dtype=float)
    if (x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all()
            or np.any(np.diff(x) <= 0) or not np.allclose(np.diff(x), x[1]-x[0])
            or densities.ndim != 2 or densities.shape[1] != len(x)
            or np.iscomplexobj(densities)):
        raise ValueError("Expected real 1D densities on a finite uniform increasing grid.")
    dx = x[1]-x[0]
    probability, means, widths = [], [], []
    for frame in densities:
        if not np.isfinite(frame).all() or np.any(frame < 0):
            raise ValueError("Probability density must be finite and nonnegative.")
        weights = frame.astype(np.float64)*dx
        norm = float(weights.sum())
        mean = float(np.dot(weights, x)/norm) if norm > 0 else np.nan
        # Centered variance avoids cancellation when the packet is far from x=0.
        width = float(np.sqrt(np.dot(weights, (x-mean)**2)/norm)) if norm > 0 else np.nan
        probability.append(norm)
        means.append(mean)
        widths.append(width)
    return {"probability": np.asarray(probability), "mean_x": np.asarray(means),
            "sigma_x": np.asarray(widths)}


def free_gaussian_moments(times, *, x0, p0, sigma0, mass=1.0, hbar=1.0):
    """Infinite-line solution with sigma0 = initial position standard deviation.

    Assumes a minimum-uncertainty Gaussian with no initial x-p correlation,
    free evolution and no absorption. sigma0 is NOT the package's width
    parameter: psi ~ exp(-((x-x0)/width)**2) has sigma0 = width/2.
    """
    times = np.asarray(times, dtype=float)
    if (times.ndim != 1 or not np.isfinite(times).all() or np.any(times < 0)
            or not np.isfinite([x0, p0, sigma0, mass, hbar]).all()
            or min(sigma0, mass, hbar) <= 0):
        raise ValueError("Reference needs finite parameters, positive mass/hbar/width and nonnegative times.")
    return {"mean_x": x0+p0*times/mass,
            "sigma_x": np.hypot(sigma0, hbar*times/(2*mass*sigma0))}


def gaussian_outside_probability(mean, sigma, lower, upper):
    """Infinite-line Gaussian probability outside a finite interval.

    A boundary-contamination warning, not an error bound for the finite-box
    evolution. Stable tail evaluation also retains very small probabilities.
    """
    mean, sigma = np.asarray(mean), np.asarray(sigma)
    if (not np.isfinite([lower, upper]).all() or lower >= upper
            or not np.isfinite(mean).all() or not np.isfinite(sigma).all()
            or np.any(sigma <= 0)):
        raise ValueError("Invalid Gaussian or interval.")
    return ndtr((lower-mean)/sigma)+ndtr((mean-upper)/sigma)
