"""Smoother helpers for `PPESolverIterative`."""

from __future__ import annotations

import numpy as np


def step_iterative_explicit(
    p: np.ndarray,
    R: np.ndarray,
    dtau: np.ndarray,
    *,
    pin: int,
    ndim: int,
) -> np.ndarray:
    """Explicit pseudo-time: p += Δτ R with frozen boundaries."""
    p = p.copy()
    for ax in range(ndim):
        s0 = [slice(None)] * ndim; s0[ax] = 0
        sN = [slice(None)] * ndim; sN[ax] = -1
        R[tuple(s0)] = 0.0
        R[tuple(sN)] = 0.0
    p += dtau * R
    p.ravel()[pin] = 0.0
    return p


def step_iterative_gauss_seidel(
    p: np.ndarray,
    R: np.ndarray,
    rho: np.ndarray,
    drho: list[np.ndarray],
    dtau: np.ndarray,
    *,
    h: list[float],
    shape,
    pin: int,
) -> np.ndarray:
    """Vectorized red-black Gauss-Seidel update."""
    Nx, Ny = shape
    hx, hy = h[0], h[1]

    inv_rho = 1.0 / rho
    ax_c = inv_rho / (hx * hx)
    ay_c = inv_rho / (hy * hy)
    bx = drho[0] / (rho ** 2 * 2.0 * hx)
    by = drho[1] / (rho ** 2 * 2.0 * hy)

    diag = 1.0 / dtau + 2.0 * ax_c + 2.0 * ay_c
    c_xm = ax_c - bx
    c_xp = ax_c + bx
    c_ym = ay_c - by
    c_yp = ay_c + by

    dp = np.zeros(shape, dtype=float)
    pin_ij = np.unravel_index(pin, shape)
    ii = np.arange(1, Nx - 1)[:, None]
    jj = np.arange(1, Ny - 1)[None, :]

    for color in range(2):
        mask = ((ii + jj) % 2 == color)
        if 1 <= pin_ij[0] < Nx - 1 and 1 <= pin_ij[1] < Ny - 1:
            mask[pin_ij[0] - 1, pin_ij[1] - 1] = False

        rhs_update = (
            R[1:-1, 1:-1]
            + c_xm[1:-1, 1:-1] * dp[:-2, 1:-1]
            + c_xp[1:-1, 1:-1] * dp[2:, 1:-1]
            + c_ym[1:-1, 1:-1] * dp[1:-1, :-2]
            + c_yp[1:-1, 1:-1] * dp[1:-1, 2:]
        )
        update_vals = rhs_update / diag[1:-1, 1:-1]
        dp[1:-1, 1:-1] = np.where(mask, update_vals, dp[1:-1, 1:-1])

    p = p + dp
    p.ravel()[pin] = 0.0
    return p


def step_iterative_adi(
    p: np.ndarray,
    R: np.ndarray,
    rho: np.ndarray,
    drho: list[np.ndarray],
    dtau: np.ndarray,
    *,
    pin: int,
    thomas_sweep,
) -> np.ndarray:
    """ADI update using the injected Thomas sweep."""
    q = thomas_sweep(R, rho, drho[0], dtau, axis=0)
    q.ravel()[pin] = 0.0
    dp = thomas_sweep(q, rho, drho[1], dtau, axis=1)
    dp.ravel()[pin] = 0.0
    p = p + dp
    p.ravel()[pin] = 0.0
    return p
