"""Boundary helper functions for `CCDSolver`."""

from __future__ import annotations

from ..backend import fuse as _fuse
from ..core.boundary import is_wall_axis


@_fuse
def _linear_comb4(c0, c1, c2, c3, f0, f1, f2, f3):
    return c0 * f0 + c1 * f1 + c2 * f2 + c3 * f3


@_fuse
def _linear_comb6(c0, c1, c2, c3, c4, c5, f0, f1, f2, f3, f4, f5):
    return c0 * f0 + c1 * f1 + c2 * f2 + c3 * f3 + c4 * f4 + c5 * f5


def _gpu_boundary_linear_comb(coeffs, values, n_terms: int):
    if n_terms == 4:
        return _linear_comb4(
            coeffs[0],
            coeffs[1],
            coeffs[2],
            coeffs[3],
            values[0],
            values[1],
            values[2],
            values[3],
        )
    if n_terms == 6:
        return _linear_comb6(
            coeffs[0],
            coeffs[1],
            coeffs[2],
            coeffs[3],
            coeffs[4],
            coeffs[5],
            values[0],
            values[1],
            values[2],
            values[3],
            values[4],
            values[5],
        )
    result = coeffs[0] * values[0]
    for idx in range(1, n_terms):
        result = result + coeffs[idx] * values[idx]
    return result


def enforce_ccd_wall_neumann(solver, grad, ax: int) -> None:
    """Zero CCD gradient at wall boundaries for Neumann conditions."""
    if not is_wall_axis(solver.bc_type, ax, solver.ndim):
        return
    sl_lo = [slice(None)] * grad.ndim
    sl_hi = [slice(None)] * grad.ndim
    sl_lo[ax] = 0
    sl_hi[ax] = -1
    grad[tuple(sl_lo)] = 0.0
    grad[tuple(sl_hi)] = 0.0


def compute_ccd_left_boundary(solver, info, f, h, bc_left_override):
    """Compute the data-dependent left boundary value."""
    xp = solver.xp
    if bc_left_override is not None:
        batch = f.shape[1]
        fp0 = xp.full(batch, float(bc_left_override[0]))
        fpp0 = xp.full(batch, float(bc_left_override[1]))
        out = xp.empty((2, batch), dtype=fp0.dtype)
        out[0] = fp0
        out[1] = fpp0
        return out

    c_I = info["c_I_left_dev"]
    c_II = info["c_II_left_dev"]
    n_II = info["n_II_left"]
    if solver.backend.device == "gpu":
        R_I = _gpu_boundary_linear_comb(c_I, f, 4)
        R_II = _gpu_boundary_linear_comb(c_II, f, n_II)
    else:
        R_I = c_I @ f[:4]
        R_II = c_II @ f[:n_II]
    out = xp.empty((2, f.shape[1]), dtype=R_I.dtype)
    out[0] = R_I
    out[1] = R_II
    return out


def compute_ccd_right_boundary(solver, info, f, h, N, bc_right_override):
    """Compute the data-dependent right boundary value."""
    xp = solver.xp
    if bc_right_override is not None:
        batch = f.shape[1]
        fpN = xp.full(batch, float(bc_right_override[0]))
        fppN = xp.full(batch, float(bc_right_override[1]))
        out = xp.empty((2, batch), dtype=fpN.dtype)
        out[0] = fpN
        out[1] = fppN
        return out

    c_I_r = info["c_I_right_dev"]
    c_II_r = info["c_II_right_dev"]
    n_II_r = info["n_II_right"]
    f_rev = f[N::-1]
    if solver.backend.device == "gpu":
        R_I_r = _gpu_boundary_linear_comb(c_I_r, f_rev, 4)
        R_II_r = _gpu_boundary_linear_comb(c_II_r, f_rev, n_II_r)
    else:
        R_I_r = c_I_r @ f_rev[:4]
        R_II_r = c_II_r @ f_rev[:n_II_r]
    out = xp.empty((2, f.shape[1]), dtype=R_I_r.dtype)
    out[0] = R_I_r
    out[1] = R_II_r
    return out
