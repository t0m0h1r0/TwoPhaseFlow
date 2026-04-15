"""GPU-friendly helpers for experiment scripts.

The production solver already routes array kernels through :class:`Backend`.
These helpers cover the experiment-side glue that is easy to leave on CPU:
sparse matrix assembly/solve wrappers, boundary masking, and scalar reductions.
They are intentionally small and work unchanged with the NumPy/SciPy backend.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp_cpu
import scipy.sparse.linalg as spla_cpu


_SPARSE_SOLVE_WARNED = False


def to_float(backend, value) -> float:
    """Return a Python float from a NumPy/CuPy scalar."""
    return float(np.asarray(backend.to_host(value)))


def max_abs_error(backend, a, b) -> float:
    """Compute ``max(abs(a-b))`` on the active backend."""
    xp = backend.xp
    return to_float(backend, xp.max(xp.abs(xp.asarray(a) - xp.asarray(b))))


def l2_norm(backend, a) -> float:
    """Compute the Euclidean norm on the active backend."""
    xp = backend.xp
    arr = xp.asarray(a)
    return to_float(backend, xp.sqrt(xp.sum(arr.ravel() * arr.ravel())))


def zero_dirichlet_boundary(arr):
    """Set a 2-D array's outer boundary to zero in-place and return it."""
    arr[0, :] = 0
    arr[-1, :] = 0
    arr[:, 0] = 0
    arr[:, -1] = 0
    return arr


def sparse_solve_2d(backend, matrix, rhs, shape=None):
    """Solve a sparse system and reshape to ``rhs.shape`` or ``shape``.

    ``matrix`` may be a SciPy or CuPy sparse matrix.  The right-hand side is
    transferred to the active backend, so GPU runs avoid a host round-trip in
    every defect-correction iteration.
    """
    xp = backend.xp
    rhs_dev = xp.asarray(rhs)
    out_shape = rhs_dev.shape if shape is None else shape
    try:
        sol = backend.sparse_linalg.spsolve(matrix, rhs_dev.ravel())
    except Exception as exc:
        if not backend.is_gpu():
            raise
        _warn_sparse_cpu_fallback(exc)
        matrix_cpu = _to_cpu_sparse(matrix)
        rhs_cpu = np.asarray(backend.to_host(rhs_dev.ravel()))
        sol = backend.xp.asarray(spla_cpu.spsolve(matrix_cpu, rhs_cpu))
    return sol.reshape(out_shape)


def _warn_sparse_cpu_fallback(exc: Exception) -> None:
    """Warn once when CuPy sparse solve is unavailable on the remote image."""
    global _SPARSE_SOLVE_WARNED
    if _SPARSE_SOLVE_WARNED:
        return
    _SPARSE_SOLVE_WARNED = True
    print(
        "WARNING: GPU sparse solve unavailable; falling back to SciPy "
        f"spsolve on CPU ({type(exc).__name__}: {exc})"
    )


def _to_cpu_sparse(matrix):
    """Return a SciPy CSR matrix from SciPy or CuPy sparse input."""
    if hasattr(matrix, "get"):
        return matrix.get().tocsr()
    return sp_cpu.csr_matrix(matrix)


def fd_laplacian_dirichlet_2d(N: int, h: float, backend):
    """2-D five-point Laplacian with identity rows on Dirichlet boundaries."""
    nx = ny = N + 1
    ii, jj = np.indices((nx, ny))
    k = (ii * ny + jj).ravel()
    boundary = (ii == 0) | (ii == N) | (jj == 0) | (jj == N)
    interior = ~boundary

    rows = [k[boundary.ravel()]]
    cols = [k[boundary.ravel()]]
    vals = [np.ones(rows[0].shape, dtype=np.float64)]

    ki = k[interior.ravel()]
    i_int = ii[interior]
    j_int = jj[interior]
    inv_h2 = 1.0 / (h * h)
    rows.extend([ki, ki, ki, ki, ki])
    cols.extend([
        (i_int + 1) * ny + j_int,
        (i_int - 1) * ny + j_int,
        i_int * ny + (j_int + 1),
        i_int * ny + (j_int - 1),
        ki,
    ])
    vals.extend([
        np.full_like(ki, inv_h2, dtype=np.float64),
        np.full_like(ki, inv_h2, dtype=np.float64),
        np.full_like(ki, inv_h2, dtype=np.float64),
        np.full_like(ki, inv_h2, dtype=np.float64),
        np.full_like(ki, -4.0 * inv_h2, dtype=np.float64),
    ])

    mat = sp_cpu.csr_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
        shape=(nx * ny, nx * ny),
    )
    return backend.sparse.csr_matrix(mat)


def fd_laplacian_neumann_2d(N: int, h: float, backend):
    """2-D five-point Laplacian with mirrored all-Neumann boundaries."""
    nx = ny = N + 1
    rows, cols, vals = [], [], []
    inv_h2 = 1.0 / (h * h)

    def idx(i, j):
        return i * ny + j

    for i in range(nx):
        for j in range(ny):
            k = idx(i, j)
            center = 0.0
            for coord, lo, hi in (
                (i, idx(i - 1, j), idx(i + 1, j)),
                (j, idx(i, j - 1), idx(i, j + 1)),
            ):
                if 0 < coord < N:
                    rows.extend((k, k))
                    cols.extend((lo, hi))
                    vals.extend((inv_h2, inv_h2))
                    center -= 2.0 * inv_h2
                elif coord == 0:
                    rows.append(k)
                    cols.append(hi)
                    vals.append(2.0 * inv_h2)
                    center -= 2.0 * inv_h2
                else:
                    rows.append(k)
                    cols.append(lo)
                    vals.append(2.0 * inv_h2)
                    center -= 2.0 * inv_h2
            rows.append(k)
            cols.append(k)
            vals.append(center)

    mat = sp_cpu.csr_matrix((vals, (rows, cols)), shape=(nx * ny, nx * ny))
    return backend.sparse.csr_matrix(mat)


def pin_gauge(matrix, rhs_flat, pin_dof: int, pin_val: float, backend):
    """Pin one row of a sparse matrix and matching RHS value."""
    mat_cpu = sp_cpu.csr_matrix(backend.to_host(matrix)).tolil()
    mat_cpu[pin_dof, :] = 0.0
    mat_cpu[pin_dof, pin_dof] = 1.0
    rhs_out = np.asarray(backend.to_host(rhs_flat)).copy()
    rhs_out[pin_dof] = pin_val
    return backend.sparse.csr_matrix(mat_cpu.tocsr()), backend.xp.asarray(rhs_out)


def fd_varrho_dirichlet_2d(N: int, h: float, rho, backend):
    """FD variable-density PPE operator with Dirichlet boundaries.

    Discretises ``(1/rho) Lap(p) - (grad rho / rho^2) . grad(p)`` with
    centered differences.  Derivatives and COO indices are vectorized on host,
    then converted to the active sparse backend.
    """
    rho_h = np.asarray(backend.to_host(rho), dtype=np.float64)
    nx = ny = N + 1
    drho_dx = np.zeros_like(rho_h)
    drho_dy = np.zeros_like(rho_h)
    drho_dx[1:N, :] = (rho_h[2:N + 1, :] - rho_h[0:N - 1, :]) / (2.0 * h)
    drho_dy[:, 1:N] = (rho_h[:, 2:N + 1] - rho_h[:, 0:N - 1]) / (2.0 * h)

    ii, jj = np.indices((nx, ny))
    k = (ii * ny + jj).ravel()
    boundary = (ii == 0) | (ii == N) | (jj == 0) | (jj == N)
    interior = ~boundary

    rows = [k[boundary.ravel()]]
    cols = [k[boundary.ravel()]]
    vals = [np.ones(rows[0].shape, dtype=np.float64)]

    ki = k[interior.ravel()]
    i_int = ii[interior]
    j_int = jj[interior]
    inv_rho = 1.0 / rho_h[interior]
    cx = drho_dx[interior] / (rho_h[interior] ** 2)
    cy = drho_dy[interior] / (rho_h[interior] ** 2)
    inv_h2 = 1.0 / (h * h)
    inv_2h = 1.0 / (2.0 * h)

    rows.extend([ki, ki, ki, ki, ki])
    cols.extend([
        (i_int + 1) * ny + j_int,
        (i_int - 1) * ny + j_int,
        i_int * ny + (j_int + 1),
        i_int * ny + (j_int - 1),
        ki,
    ])
    vals.extend([
        inv_rho * inv_h2 - cx * inv_2h,
        inv_rho * inv_h2 + cx * inv_2h,
        inv_rho * inv_h2 - cy * inv_2h,
        inv_rho * inv_h2 + cy * inv_2h,
        -4.0 * inv_rho * inv_h2,
    ])

    mat = sp_cpu.csr_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
        shape=(nx * ny, nx * ny),
    )
    return backend.sparse.csr_matrix(mat)
