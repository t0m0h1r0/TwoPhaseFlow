"""Residual helpers for `PPESolverIterative`."""

from __future__ import annotations

import numpy as np


def compute_density_gradient_3pt(rho_np: np.ndarray, *, h: list[float], ndim: int) -> list[np.ndarray]:
    """Compute ∂ρ/∂x_i via 3-point central differences."""
    drho: list[np.ndarray] = []
    for ax in range(ndim):
        h_ax = h[ax]
        dr = np.zeros_like(rho_np)
        slc_p = [slice(None)] * ndim
        slc_m = [slice(None)] * ndim
        slc_c = [slice(None)] * ndim
        slc_p[ax] = slice(2, None)
        slc_m[ax] = slice(None, -2)
        slc_c[ax] = slice(1, -1)
        dr[tuple(slc_c)] = (rho_np[tuple(slc_p)] - rho_np[tuple(slc_m)]) / (2.0 * h_ax)
        s0 = [slice(None)] * ndim; s0[ax] = 0
        s1 = [slice(None)] * ndim; s1[ax] = 1
        s2 = [slice(None)] * ndim; s2[ax] = 2
        dr[tuple(s0)] = (
            -3.0 * rho_np[tuple(s0)]
            + 4.0 * rho_np[tuple(s1)]
            - rho_np[tuple(s2)]
        ) / (2.0 * h_ax)
        sN = [slice(None)] * ndim; sN[ax] = -1
        sNm1 = [slice(None)] * ndim; sNm1[ax] = -2
        sNm2 = [slice(None)] * ndim; sNm2[ax] = -3
        dr[tuple(sN)] = (
            3.0 * rho_np[tuple(sN)]
            - 4.0 * rho_np[tuple(sNm1)]
            + rho_np[tuple(sNm2)]
        ) / (2.0 * h_ax)
        drho.append(dr)
    return drho


def compute_iterative_residual_3pt(
    p: np.ndarray,
    rhs_np: np.ndarray,
    rho_np: np.ndarray,
    drho: list[np.ndarray],
    *,
    h: list[float],
    ndim: int,
    shape,
) -> tuple[np.ndarray, list[np.ndarray], list[np.ndarray]]:
    """Return `(rhs - L_FD(p), dp_list, d2p_list)` for the 3-point scheme."""
    Lp = np.zeros(shape, dtype=float)
    dp_list: list[np.ndarray] = []
    d2p_list: list[np.ndarray] = []
    for ax in range(ndim):
        h_ax = h[ax]
        h2 = h_ax * h_ax
        slc_p = [slice(None)] * ndim
        slc_m = [slice(None)] * ndim
        slc_c = [slice(None)] * ndim
        slc_p[ax] = slice(2, None)
        slc_m[ax] = slice(None, -2)
        slc_c[ax] = slice(1, -1)
        d2p = np.zeros(shape, dtype=float)
        d2p[tuple(slc_c)] = (
            p[tuple(slc_p)] - 2.0 * p[tuple(slc_c)] + p[tuple(slc_m)]
        ) / h2
        dp_ax = np.zeros(shape, dtype=float)
        dp_ax[tuple(slc_c)] = (
            p[tuple(slc_p)] - p[tuple(slc_m)]
        ) / (2.0 * h_ax)
        Lp += d2p / rho_np - (drho[ax] / rho_np ** 2) * dp_ax
        dp_list.append(dp_ax)
        d2p_list.append(d2p)
    return rhs_np - Lp, dp_list, d2p_list
