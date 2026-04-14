"""
PPE solver diagnostics (separated from production solver per SRP).

These functions are for tests and validation scripts only — not part
of the solve pipeline. They are expensive (recompute full CCD operator).
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend
    from ..core.boundary import BoundarySpec


def ccd_ppe_residual(
    p, rhs, rho,
    ccd: "CCDSolver",
    backend: "Backend",
    bc_spec: "BoundarySpec",
    grid_shape: tuple,
    ndim: int,
) -> float:
    """Compute ||L_CCD^rho p - rhs||_2 (diagnostic only).

    The pin node is excluded from the residual since it carries a gauge
    constraint, not a PDE equation.

    Parameters
    ----------
    p, rhs, rho : arrays of shape grid_shape
    ccd         : CCDSolver
    backend     : Backend
    bc_spec     : BoundarySpec (provides pin_dof)
    grid_shape  : tuple
    ndim        : int

    Returns
    -------
    residual : float — L2 norm of the residual
    """
    xp = backend.xp
    rho_dev = xp.asarray(backend.to_host(rho))
    drho = []
    for ax in range(ndim):
        drho_ax, _ = ccd.differentiate(rho_dev, ax)
        drho.append(drho_ax)

    p_dev = xp.asarray(backend.to_host(p))
    Lp = xp.zeros(grid_shape, dtype=p_dev.dtype)
    for ax in range(ndim):
        dp_ax, d2p_ax = ccd.differentiate(p_dev, ax)
        Lp += d2p_ax / rho_dev - (drho[ax] / rho_dev ** 2) * dp_ax

    rhs_dev = xp.asarray(backend.to_host(rhs))
    residual = Lp - rhs_dev
    pin_dof = bc_spec.pin_dof
    residual_arr = np.asarray(backend.to_host(residual))
    residual_arr.ravel()[pin_dof] = 0.0
    return float(np.sqrt(np.sum(residual_arr ** 2)))
