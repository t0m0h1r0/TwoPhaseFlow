"""
Field-level diagnostics: kinetic energy, divergence.

Pure functions extracted from experiment scripts (ch11, ch12).
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver


def kinetic_energy(velocity_components, cell_volumes) -> float:
    """Kinetic energy: E_k = (1/2) sum_i (u_i^2 + v_i^2 + ...) * dV_i.

    Parameters
    ----------
    velocity_components : list of arrays [u, v[, w]]
    cell_volumes        : array of per-node control volumes

    Returns
    -------
    E_k : float
    """
    sq_sum = sum(u ** 2 for u in velocity_components)
    return 0.5 * float(np.sum(sq_sum * cell_volumes))


def kinetic_energy_periodic(velocity_components, h: float) -> float:
    """Kinetic energy on a periodic grid (exclude endpoint duplicates).

    E_k = (h^2 / 2) * sum(u[:-1,:-1]^2 + v[:-1,:-1]^2)

    Parameters
    ----------
    velocity_components : list of 2-D arrays [u, v]
    h                   : uniform grid spacing
    """
    interior = [u[:-1, :-1] for u in velocity_components]
    sq_sum = sum(u ** 2 for u in interior)
    return 0.5 * h ** 2 * float(np.sum(sq_sum))


def divergence_linf(velocity_components, ccd: "CCDSolver") -> float:
    """L-infinity norm of velocity divergence via CCD.

    ||div(u)||_inf = max |du/dx + dv/dy [+ dw/dz]|
    """
    div = _compute_divergence(velocity_components, ccd)
    return float(np.max(np.abs(div)))


def divergence_l2(velocity_components, ccd: "CCDSolver") -> float:
    """L2 norm of velocity divergence via CCD.

    ||div(u)||_2 = sqrt(sum(div^2))
    """
    div = _compute_divergence(velocity_components, ccd)
    return float(np.sqrt(np.sum(div ** 2)))


def _compute_divergence(velocity_components, ccd):
    """Compute divergence field via CCD differentiation."""
    div = np.zeros_like(velocity_components[0])
    for ax, u in enumerate(velocity_components):
        du_dax, _ = ccd.differentiate(u, ax)
        div = div + np.asarray(du_dax)
    return div
