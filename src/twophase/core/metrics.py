"""
Grid metric computation (J = dxi/dx, dJ/dxi).

Extracted from Grid._build_metrics() for SRP and testability.
Supports both CCD (O(h^6)) and central-difference (O(h^2)) paths.

Equations (section 4.9):
    df/dx   = J * (df/dxi)
    d2f/dx2 = J^2 * (d2f/dxi2) + J * (dJ/dxi) * (df/dxi)
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING, Tuple, List

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver


def compute_metrics(
    coords: List[np.ndarray],
    h: List[np.ndarray],
    N: tuple,
    ndim: int,
    uniform: bool,
    ccd: "CCDSolver | None" = None,
) -> Tuple[List[np.ndarray], List[np.ndarray]]:
    """Compute J = dxi/dx and dJ/dxi for each axis.

    Parameters
    ----------
    coords  : per-axis node coordinate arrays
    h       : per-axis node spacing arrays
    N       : cells per axis
    ndim    : number of dimensions
    uniform : True if grid is uniform (alpha_grid <= 1)
    ccd     : CCDSolver for O(h^6) metric evaluation (optional)

    Returns
    -------
    J       : list of per-axis metric arrays
    dJ_dxi  : list of per-axis metric gradient arrays
    """
    J: List[np.ndarray] = []
    dJ_dxi: List[np.ndarray] = []

    for ax in range(ndim):
        if ccd is not None and not uniform:
            # CCD O(h^6): differentiate x(xi) in xi-space
            coords_ax = np.asarray(coords[ax])
            d1_raw, d2_raw = ccd.differentiate_raw(coords_ax, axis=ax)
            J_ax = 1.0 / d1_raw
            dJ_ax = -d2_raw / (d1_raw ** 2)
        else:
            # O(h^2) central-difference fallback
            dxi = 1.0 / N[ax]
            h_ax = h[ax]
            J_ax = dxi / h_ax

            dJ_ax = np.zeros_like(J_ax)
            dJ_ax[1:-1] = (J_ax[2:] - J_ax[:-2]) / (2.0 * dxi)
            dJ_ax[0] = (J_ax[1] - J_ax[0]) / dxi
            dJ_ax[-1] = (J_ax[-1] - J_ax[-2]) / dxi

        J.append(J_ax)
        dJ_dxi.append(dJ_ax)

    return J, dJ_dxi
