"""
Interface-level diagnostics: thickness, area, parasitic currents, tracking.

Pure functions extracted from experiment scripts (ch12).
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING

from ...backend import host_array, scalar_value

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver


def measure_eps_eff(xp, psi, ccd: "CCDSolver", eps_nominal: float) -> float:
    """Estimate effective interface thickness from psi(1-psi)/|grad(psi)|.

    Uses median in the interface band (0.05 < psi < 0.95) for robustness
    against corner spikes.

    Parameters
    ----------
    xp           : array namespace (numpy or cupy)
    psi          : CLS field
    ccd          : CCDSolver for gradient computation
    eps_nominal  : nominal interface thickness (fallback)

    Returns
    -------
    eps_eff : float — estimated effective thickness
    """
    grad_sq = xp.zeros_like(psi)
    for ax in range(psi.ndim):
        g1, _ = ccd.differentiate(psi, ax)
        grad_sq = grad_sq + g1 * g1
    grad_psi = xp.sqrt(xp.maximum(grad_sq, 1e-28))

    band = (psi > 0.05) & (psi < 0.95)
    psi_1mpsi = psi * (1.0 - psi)
    if scalar_value(xp.any(band)):
        eps_local = psi_1mpsi[band] / xp.maximum(grad_psi[band], 1e-14)
        return scalar_value(xp.median(eps_local))
    return eps_nominal


def interface_area(xp, psi, grid) -> float:
    """Interface area (2-D: length) from CLS field: A = integral(psi * dV).

    Parameters
    ----------
    xp   : array namespace
    psi  : CLS field
    grid : Grid object

    Returns
    -------
    area : float
    """
    dV = grid.cell_volumes()
    return scalar_value(xp.sum(psi * dV))


def parasitic_current_linf(velocity_components) -> float:
    """L-infinity parasitic current magnitude: max(sqrt(u^2 + v^2 + ...)).

    For a static droplet at equilibrium, this should be close to zero.
    Non-zero values indicate balanced-force violations.
    """
    sq_sum = sum(host_array(u) ** 2 for u in velocity_components)
    return float(np.max(np.sqrt(sq_sum)))


def find_interface_crossing(field, coords_1d, threshold: float = 0.5):
    """Find the coordinate where field crosses threshold (linear interpolation).

    Searches along a 1-D slice for the first crossing.

    Parameters
    ----------
    field      : 1-D array
    coords_1d  : 1-D coordinate array (same length)
    threshold  : crossing value (default 0.5 for CLS)

    Returns
    -------
    crossing : float or nan if no crossing found
    """
    f = np.asarray(field).ravel()
    c = np.asarray(coords_1d).ravel()
    for j in range(len(f) - 1):
        if (f[j] - threshold) * (f[j + 1] - threshold) < 0:
            t = (threshold - f[j]) / (f[j + 1] - f[j])
            return float(c[j] + t * (c[j + 1] - c[j]))
    return float('nan')


def midband_fraction(psi, lo: float = 0.1, hi: float = 0.9) -> float:
    """Fraction of cells with lo < psi < hi (interface-band occupancy)."""
    q = host_array(psi)
    if q.size == 0:
        return float("nan")
    return float(((q > lo) & (q < hi)).mean())


def relative_mass_error(psi, dV, mass_ref: float) -> float:
    """Relative mass error |∫psi dV - mass_ref| / |mass_ref|."""
    q = host_array(psi)
    vol = host_array(dV)
    m = float(np.sum(q * vol))
    return float(abs(m - mass_ref) / max(abs(mass_ref), 1e-30))
