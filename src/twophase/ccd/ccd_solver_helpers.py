"""Helper utilities for `CCDSolver` wall/periodic solve paths."""

from __future__ import annotations

import math
import numpy as np

from .block_tridiag import BlockTridiagSolver


def _solve_dense_inverse_or_lu(solver, info, rhs_flat):
    if solver.backend.device == "gpu":
        A_inv_dev_T = info.get('A_inv_dev_T')
        if A_inv_dev_T is not None:
            return (rhs_flat.T @ A_inv_dev_T).T
        return info['A_inv_dev'] @ rhs_flat
    return solver.backend.linalg.lu_solve((info['lu'], info['piv']), rhs_flat)


def differentiate_ccd_wall_raw(solver, data, axis: int, bc_left, bc_right):
    xp = solver.xp
    info = solver._solvers[axis]
    h = info['h']
    N = info['N']
    n_int = info['n_int']

    data = xp.asarray(data)
    f = xp.moveaxis(data, axis, 0)
    orig_shape = f.shape
    n_pts = f.shape[0]
    batch_size = math.prod(orig_shape[1:]) if len(orig_shape) > 1 else 1
    f = f.reshape(n_pts, batch_size)

    f_m1 = f[0:n_int]
    f_0 = f[1:n_int + 1]
    f_p1 = f[2:n_int + 2]
    d1_rhs = (_A1 / h) * (f_p1 - f_m1)
    d2_rhs = (_A2 / (h * h)) * (f_m1 - 2.0 * f_0 + f_p1)
    rhs = xp.empty((n_int, 2, batch_size), dtype=f.dtype)
    rhs[:, 0, :] = d1_rhs
    rhs[:, 1, :] = d2_rhs

    bc_lo = solver._left_boundary(info, f, h, bc_left)
    bc_hi = solver._right_boundary(info, f, h, N, bc_right)
    rhs[0] -= info['L0_dev'] @ bc_lo
    rhs[-1] -= info['UN_dev'] @ bc_hi

    rhs_flat = rhs.reshape(2 * n_int, -1)
    x_flat = _solve_dense_inverse_or_lu(solver, info, rhs_flat)
    sol = x_flat.reshape(n_int, 2, -1)

    out = xp.empty((2, n_pts, batch_size))
    out[:, 1:-1, :] = sol.transpose(1, 0, 2)
    out[:, 0, :] = info['M_left_dev'] @ out[:, 1, :] + bc_lo
    out[:, N, :] = info['M_right_dev'] @ out[:, N - 1, :] + bc_hi

    d1 = xp.moveaxis(out[0].reshape(orig_shape), 0, axis)
    d2 = xp.moveaxis(out[1].reshape(orig_shape), 0, axis)
    return d1, d2


def differentiate_ccd_wall_first_only(solver, data, axis: int, bc_left, bc_right, apply_metric: bool = True):
    xp = solver.xp
    info = solver._solvers[axis]
    h = info['h']
    N = info['N']
    n_int = info['n_int']

    data = xp.asarray(data)
    f = xp.moveaxis(data, axis, 0)
    orig_shape = f.shape
    n_pts = f.shape[0]
    batch_size = math.prod(orig_shape[1:]) if len(orig_shape) > 1 else 1
    f = f.reshape(n_pts, batch_size)

    f_m1 = f[0:n_int]
    f_0 = f[1:n_int + 1]
    f_p1 = f[2:n_int + 2]
    d1_rhs = (_A1 / h) * (f_p1 - f_m1)
    d2_rhs = (_A2 / (h * h)) * (f_m1 - 2.0 * f_0 + f_p1)
    rhs = xp.empty((n_int, 2, batch_size), dtype=f.dtype)
    rhs[:, 0, :] = d1_rhs
    rhs[:, 1, :] = d2_rhs

    bc_lo = solver._left_boundary(info, f, h, bc_left)
    bc_hi = solver._right_boundary(info, f, h, N, bc_right)
    rhs[0] -= info['L0_dev'] @ bc_lo
    rhs[-1] -= info['UN_dev'] @ bc_hi

    rhs_flat = rhs.reshape(2 * n_int, -1)
    x_flat = _solve_dense_inverse_or_lu(solver, info, rhs_flat)
    sol = x_flat.reshape(n_int, 2, -1)

    left_pair = info['M_left_dev'] @ sol[0] + bc_lo
    right_pair = info['M_right_dev'] @ sol[-1] + bc_hi

    d1_flat = xp.empty((n_pts, batch_size), dtype=f.dtype)
    d1_flat[1:-1, :] = sol[:, 0, :]
    d1_flat[0, :] = left_pair[0]
    d1_flat[N, :] = right_pair[0]
    d1_axis0 = d1_flat.reshape(orig_shape)

    if not solver.grid.uniform and apply_metric:
        shape = [-1] + [1] * (len(orig_shape) - 1)
        d1_axis0 = xp.asarray(solver.grid.J[axis]).reshape(shape) * d1_axis0

    return xp.moveaxis(d1_axis0, 0, axis)


def differentiate_ccd_wall_second_only(solver, data, axis: int, bc_left, bc_right, apply_metric: bool = True):
    xp = solver.xp
    info = solver._solvers[axis]
    h = info['h']
    N = info['N']
    n_int = info['n_int']

    data = xp.asarray(data)
    f = xp.moveaxis(data, axis, 0)
    orig_shape = f.shape
    n_pts = f.shape[0]
    batch_size = math.prod(orig_shape[1:]) if len(orig_shape) > 1 else 1
    f = f.reshape(n_pts, batch_size)

    f_m1 = f[0:n_int]
    f_0 = f[1:n_int + 1]
    f_p1 = f[2:n_int + 2]
    d1_rhs = (_A1 / h) * (f_p1 - f_m1)
    d2_rhs = (_A2 / (h * h)) * (f_m1 - 2.0 * f_0 + f_p1)
    rhs = xp.empty((n_int, 2, batch_size), dtype=f.dtype)
    rhs[:, 0, :] = d1_rhs
    rhs[:, 1, :] = d2_rhs

    bc_lo = solver._left_boundary(info, f, h, bc_left)
    bc_hi = solver._right_boundary(info, f, h, N, bc_right)
    rhs[0] -= info['L0_dev'] @ bc_lo
    rhs[-1] -= info['UN_dev'] @ bc_hi

    rhs_flat = rhs.reshape(2 * n_int, -1)
    x_flat = _solve_dense_inverse_or_lu(solver, info, rhs_flat)
    sol = x_flat.reshape(n_int, 2, -1)

    left_pair = info['M_left_dev'] @ sol[0] + bc_lo
    right_pair = info['M_right_dev'] @ sol[-1] + bc_hi

    d2_flat = xp.empty((n_pts, batch_size), dtype=f.dtype)
    d2_flat[1:-1, :] = sol[:, 1, :]
    d2_flat[0, :] = left_pair[1]
    d2_flat[N, :] = right_pair[1]
    d2_axis0 = d2_flat.reshape(orig_shape)

    if not solver.grid.uniform and apply_metric:
        d1_flat = xp.empty((n_pts, batch_size), dtype=f.dtype)
        d1_flat[1:-1, :] = sol[:, 0, :]
        d1_flat[0, :] = left_pair[0]
        d1_flat[N, :] = right_pair[0]
        d1_axis0 = d1_flat.reshape(orig_shape)
        shape = [-1] + [1] * (len(orig_shape) - 1)
        J = xp.asarray(solver.grid.J[axis]).reshape(shape)
        dJ = xp.asarray(solver.grid.dJ_dxi[axis]).reshape(shape)
        d2_axis0 = J * J * d2_axis0 + J * dJ * d1_axis0

    return xp.moveaxis(d2_axis0, 0, axis)


def build_ccd_axis_solver(solver, n_pts: int, h: float, boundary_coeffs_left, boundary_coeffs_right) -> dict:
    N = n_pts - 1
    n_int = N - 1
    assert n_int >= 1, f"Need ≥ 3 grid points; got {n_pts}"

    bc_left = boundary_coeffs_left(h, n_pts)
    bc_right = boundary_coeffs_right(h, n_pts)

    L0 = np.array([[_ALPHA1, _B1 * h], [_B2 / h, _BETA2]])
    UN = np.array([[_ALPHA1, -_B1 * h], [-_B2 / h, _BETA2]])

    diag = [np.eye(2) for _ in range(n_int)]
    lower = [np.array([[_ALPHA1, _B1 * h], [_B2 / h, _BETA2]]) for _ in range(n_int)]
    upper = [np.array([[_ALPHA1, -_B1 * h], [-_B2 / h, _BETA2]]) for _ in range(n_int)]

    diag[0] = diag[0] + lower[0] @ bc_left['M']
    lower[0] = np.zeros((2, 2))
    diag[-1] = diag[-1] + upper[-1] @ bc_right['M']
    upper[-1] = np.zeros((2, 2))

    A_host = np.zeros((2 * n_int, 2 * n_int))
    for i in range(n_int):
        A_host[2*i:2*i+2, 2*i:2*i+2] = diag[i]
        if i >= 1:
            A_host[2*i:2*i+2, 2*(i-1):2*(i-1)+2] = lower[i]
        if i <= n_int - 2:
            A_host[2*i:2*i+2, 2*(i+1):2*(i+1)+2] = upper[i]

    A_dev = solver.xp.asarray(A_host)
    lu, piv = solver.backend.linalg.lu_factor(A_dev)

    xp = solver.xp
    if solver.backend.device == "gpu":
        A_inv_dev = solver.backend.linalg.lu_solve((lu, piv), xp.eye(2 * n_int, dtype=A_dev.dtype))
    else:
        A_inv_dev = None

    info_dev = {
        'A_inv_dev': A_inv_dev,
        'L0_dev': xp.asarray(L0),
        'UN_dev': xp.asarray(UN),
        'M_left_dev': xp.asarray(bc_left['M']),
        'M_right_dev': xp.asarray(bc_right['M']),
        'c_I_left_dev': xp.asarray(bc_left['c_I']),
        'c_II_left_dev': xp.asarray(bc_left['c_II']),
        'c_I_right_dev': xp.asarray(bc_right['c_I']),
        'c_II_right_dev': xp.asarray(bc_right['c_II']),
        'n_I_left': len(bc_left['c_I']),
        'n_II_left': len(bc_left['c_II']),
        'n_I_right': len(bc_right['c_I']),
        'n_II_right': len(bc_right['c_II']),
    }

    return {
        'lu': lu,
        'piv': piv,
        'h': h,
        'N': N,
        'n_int': n_int,
        'L0': L0,
        'UN': UN,
        'bc_left': bc_left,
        'bc_right': bc_right,
        **info_dev,
    }


def build_ccd_axis_solver_legacy(solver, n_pts: int, h: float, boundary_coeffs_left, boundary_coeffs_right) -> dict:
    N = n_pts - 1
    n_int = N - 1
    assert n_int >= 1, f"Need ≥ 3 grid points; got {n_pts}"

    bc_left = boundary_coeffs_left(h, n_pts)
    bc_right = boundary_coeffs_right(h, n_pts)

    L0 = np.array([[_ALPHA1, _B1 * h], [_B2 / h, _BETA2]])
    UN = np.array([[_ALPHA1, -_B1 * h], [-_B2 / h, _BETA2]])

    diag = [np.eye(2) for _ in range(n_int)]
    lower = [np.array([[_ALPHA1, _B1 * h], [_B2 / h, _BETA2]]) for _ in range(n_int)]
    upper = [np.array([[_ALPHA1, -_B1 * h], [-_B2 / h, _BETA2]]) for _ in range(n_int)]

    diag[0] = diag[0] + lower[0] @ bc_left['M']
    lower[0] = np.zeros((2, 2))
    diag[-1] = diag[-1] + upper[-1] @ bc_right['M']
    upper[-1] = np.zeros((2, 2))

    solver_legacy = BlockTridiagSolver(solver.xp)
    solver_legacy.factorize(diag, lower, upper)

    return {
        'solver': solver_legacy,
        'h': h,
        'N': N,
        'n_int': n_int,
        'L0': L0,
        'UN': UN,
        'bc_left': bc_left,
        'bc_right': bc_right,
    }


def build_ccd_axis_solver_periodic(solver, n_pts: int, h: float) -> dict:
    N = n_pts - 1
    assert N >= 3, f"Need ≥ 3 unique nodes for periodic CCD; got {N}"

    lower_blk = np.array([[_ALPHA1, _B1 * h], [_B2 / h, _BETA2]])
    upper_blk = np.array([[_ALPHA1, -_B1 * h], [-_B2 / h, _BETA2]])

    A_host = np.zeros((2 * N, 2 * N))
    for i in range(N):
        A_host[2*i:2*i+2, 2*i:2*i+2] += np.eye(2)
        j_lo = (i - 1) % N
        A_host[2*i:2*i+2, 2*j_lo:2*j_lo+2] += lower_blk
        j_hi = (i + 1) % N
        A_host[2*i:2*i+2, 2*j_hi:2*j_hi+2] += upper_blk

    A_dev = solver.xp.asarray(A_host)
    lu, piv = solver.backend.linalg.lu_factor(A_dev)
    return {'lu': lu, 'piv': piv, 'h': h, 'N': N}


def differentiate_ccd_periodic(solver, data, axis: int, apply_metric: bool = True):
    xp = solver.xp
    info = solver._periodic_solvers[axis]
    h = info['h']
    N = info['N']

    data = xp.asarray(data)
    f_full = xp.moveaxis(data, axis, 0)
    orig_shape = f_full.shape
    n_pts = f_full.shape[0]
    batch_size = math.prod(orig_shape[1:]) if len(orig_shape) > 1 else 1
    f_full = f_full.reshape(n_pts, batch_size)
    f_unique = f_full[:N, :]

    f_im1 = xp.roll(f_unique, 1, axis=0)
    f_ip1 = xp.roll(f_unique, -1, axis=0)
    rhs_d1 = (_A1 / h) * (f_ip1 - f_im1)
    rhs_d2 = (_A2 / (h * h)) * (f_im1 - 2.0 * f_unique + f_ip1)

    rhs = xp.empty((2 * N, batch_size), dtype=f_unique.dtype)
    rhs[0::2, :] = rhs_d1
    rhs[1::2, :] = rhs_d2

    x = solver.backend.linalg.lu_solve((info['lu'], info['piv']), rhs)
    d1_inner = x[0::2, :]
    d2_inner = x[1::2, :]

    d1_flat = xp.empty((N + 1, batch_size), dtype=f_unique.dtype)
    d2_flat = xp.empty((N + 1, batch_size), dtype=f_unique.dtype)
    d1_flat[:N, :] = d1_inner
    d2_flat[:N, :] = d2_inner
    d1_flat[N, :] = d1_inner[0, :]
    d2_flat[N, :] = d2_inner[0, :]

    d1 = xp.moveaxis(d1_flat.reshape(orig_shape), 0, axis)
    d2 = xp.moveaxis(d2_flat.reshape(orig_shape), 0, axis)

    if not solver.grid.uniform and apply_metric:
        d1, d2 = apply_ccd_metric(solver, d1, d2, axis)
    return d1, d2


def differentiate_ccd_periodic_second_only(solver, data, axis: int, apply_metric: bool = True):
    xp = solver.xp
    info = solver._periodic_solvers[axis]
    h = info['h']
    N = info['N']

    data = xp.asarray(data)
    f_full = xp.moveaxis(data, axis, 0)
    orig_shape = f_full.shape
    n_pts = f_full.shape[0]
    batch_size = math.prod(orig_shape[1:]) if len(orig_shape) > 1 else 1
    f_full = f_full.reshape(n_pts, batch_size)
    f_unique = f_full[:N, :]

    f_im1 = xp.roll(f_unique, 1, axis=0)
    f_ip1 = xp.roll(f_unique, -1, axis=0)
    rhs_d1 = (_A1 / h) * (f_ip1 - f_im1)
    rhs_d2 = (_A2 / (h * h)) * (f_im1 - 2.0 * f_unique + f_ip1)

    rhs = xp.empty((2 * N, batch_size), dtype=f_unique.dtype)
    rhs[0::2, :] = rhs_d1
    rhs[1::2, :] = rhs_d2

    x = solver.backend.linalg.lu_solve((info['lu'], info['piv']), rhs)
    d2_inner = x[1::2, :]
    d2_flat = xp.empty((N + 1, batch_size), dtype=f_unique.dtype)
    d2_flat[:N, :] = d2_inner
    d2_flat[N, :] = d2_inner[0, :]
    d2 = xp.moveaxis(d2_flat.reshape(orig_shape), 0, axis)

    if not solver.grid.uniform and apply_metric:
        d1_inner = x[0::2, :]
        d1_flat = xp.empty((N + 1, batch_size), dtype=f_unique.dtype)
        d1_flat[:N, :] = d1_inner
        d1_flat[N, :] = d1_inner[0, :]
        d1 = xp.moveaxis(d1_flat.reshape(orig_shape), 0, axis)
        _, d2 = apply_ccd_metric(solver, d1, d2, axis)

    return d2


def apply_ccd_metric(solver, d1_xi, d2_xi, axis: int):
    xp = solver.xp
    J_1d = xp.asarray(solver.grid.J[axis])
    dJ_1d = xp.asarray(solver.grid.dJ_dxi[axis])
    shape = [1] * solver.ndim
    shape[axis] = -1
    J = J_1d.reshape(shape)
    dJ = dJ_1d.reshape(shape)
    d1_x = J * d1_xi
    d2_x = J * J * d2_xi + J * dJ * d1_xi
    return d1_x, d2_x


_ALPHA1 = 7.0 / 16.0
_A1 = 15.0 / 16.0
_B1 = 1.0 / 16.0
_BETA2 = -1.0 / 8.0
_A2 = 3.0
_B2 = -9.0 / 8.0
