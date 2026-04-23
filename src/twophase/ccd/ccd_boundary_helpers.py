"""Boundary helper functions for `CCDSolver`."""

from __future__ import annotations


def enforce_ccd_wall_neumann(solver, grad, ax: int) -> None:
    """Zero CCD gradient at wall boundaries for Neumann conditions."""
    if solver.bc_type != "wall":
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
    R_I_r = c_I_r @ f_rev[:4]
    R_II_r = c_II_r @ f_rev[:n_II_r]
    out = xp.empty((2, f.shape[1]), dtype=R_I_r.dtype)
    out[0] = R_I_r
    out[1] = R_II_r
    return out
