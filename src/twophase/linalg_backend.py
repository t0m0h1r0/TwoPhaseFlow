"""
Backend-agnostic linear algebra helpers.

Hosts the one numerical routine that does not have a direct ``cupyx``
equivalent: a batched tridiagonal (Thomas) solver used by the compact
filters in :mod:`twophase.levelset.compact_filters`.

On CPU (NumPy) the textbook Thomas sweep is used: forward elimination +
back substitution across all batch dimensions with pre-computed scalar
factors, costing 2n Python→kernel dispatches per call.

On GPU (CuPy) ``thomas_batched`` routes to ``_pcr_solve_batched``, a
Parallel Cyclic Reduction (PCR) implementation that completes in
ceil(log₂ n) fully-vectorised stages — 14 kernel launches for n=129
versus 258 for the sequential Thomas sweep.  Each PCR stage applies
xp.roll-based neighbour access and elementwise arithmetic across all
(n × B) elements simultaneously, keeping the GPU saturated.

Stability
---------
Unpivoted Thomas / PCR are both stable iff the tridiagonal matrix is
diagonally dominant.  The only consumers (Helmholtz-κ and Lele/Kim Padé
filters) build *diagonally dominant* LHS matrices by construction, so no
pivoting is required.  Do not use these solvers on general banded systems.
"""

from __future__ import annotations

import math
from .linalg_backend_helpers import (
    ThomasFactors,
    reshape_batched_rhs,
    restore_batched_rhs,
    thomas_precompute,
    validate_banded_tridiag_shape,
)


def _is_cupy(xp) -> bool:
    return getattr(xp, '__name__', '') == 'cupy'


def _pcr_solve_batched(xp, a_vec, d_vec, c_vec, b_mat):
    """Parallel Cyclic Reduction for batched tridiagonal systems.

    Solves ``a[i]*x[i-1] + d[i]*x[i] + c[i]*x[i+1] = b[:,i]`` for all
    batch columns simultaneously using ceil(log₂ n) fully-vectorised stages.

    Parameters
    ----------
    a_vec, d_vec, c_vec : (n,) xp arrays — lower / main / upper diagonal.
        a[0] and c[n-1] are ignored (boundary).
    b_mat : (n, B) xp array — batched right-hand sides (modified in place).

    Returns
    -------
    x : (n, B) xp array — solution.
    """
    n = a_vec.shape[0]
    n_stages = max(1, math.ceil(math.log2(n)))

    # Expand diagonals to (n, 1) for unified broadcasting with (n, B) b_mat.
    lower_coeff = xp.asarray(a_vec, dtype=b_mat.dtype)[:, None]
    diag_coeff = xp.asarray(d_vec, dtype=b_mat.dtype)[:, None]
    upper_coeff = xp.asarray(c_vec, dtype=b_mat.dtype)[:, None]
    rhs_work = b_mat.copy()
    return _pcr_reduce_batched(
        xp,
        lower_coeff,
        diag_coeff,
        upper_coeff,
        rhs_work,
        n_stages,
    )


def _pcr_reduce_batched(
    xp,
    lower_coeff,
    diag_coeff,
    upper_coeff,
    rhs_work,
    n_stages: int,
):
    """Run the shared PCR reduction loop for batched tridiagonal systems."""
    n = diag_coeff.shape[0]
    line_index = xp.arange(n)
    stride = 1
    for _ in range(n_stages):
        diag_left = xp.roll(diag_coeff, stride, axis=0)
        upper_left = xp.roll(upper_coeff, stride, axis=0)
        lower_left = xp.roll(lower_coeff, stride, axis=0)
        rhs_left = xp.roll(rhs_work, stride, axis=0)

        diag_right = xp.roll(diag_coeff, -stride, axis=0)
        lower_right = xp.roll(lower_coeff, -stride, axis=0)
        upper_right = xp.roll(upper_coeff, -stride, axis=0)
        rhs_right = xp.roll(rhs_work, -stride, axis=0)

        has_left = (line_index >= stride)[:, None]
        diag_left_safe = xp.where(xp.abs(diag_left) > 0, diag_left, 1.0)
        alpha = xp.where(has_left, -lower_coeff / diag_left_safe, 0.0)

        has_right = (line_index < n - stride)[:, None]
        diag_right_safe = xp.where(xp.abs(diag_right) > 0, diag_right, 1.0)
        beta = xp.where(has_right, -upper_coeff / diag_right_safe, 0.0)

        lower_coeff = alpha * lower_left
        diag_coeff = diag_coeff + alpha * upper_left + beta * lower_right
        upper_coeff = beta * upper_right
        rhs_work = rhs_work + alpha * rhs_left + beta * rhs_right

        stride *= 2

    return rhs_work / diag_coeff


def _pcr_solve_variable_batched(xp, a_mat, d_mat, c_mat, b_mat, max_stages: int | None = None):
    """Parallel Cyclic Reduction for variable-coefficient batched systems.

    Solves independent tridiagonal systems

        a[i, b] x[i-1, b] + d[i, b] x[i, b] + c[i, b] x[i+1, b] = b[i, b]

    for every batch column ``b`` simultaneously.  Unlike
    :func:`_pcr_solve_batched`, the tridiagonal coefficients may vary across
    batch columns.

    Parameters
    ----------
    a_mat, d_mat, c_mat : (n, B) xp.ndarray
        Lower / main / upper diagonals. ``a_mat[0]`` and ``c_mat[n-1]`` are
        ignored.
    b_mat : (n, B) xp.ndarray
        Right-hand side.

    Returns
    -------
    x : (n, B) xp.ndarray
        Solution.
    """
    if a_mat.shape != d_mat.shape or a_mat.shape != c_mat.shape:
        raise ValueError("a_mat, d_mat, c_mat must share the same shape")
    if b_mat.shape != d_mat.shape:
        raise ValueError("b_mat must have the same shape as the diagonals")

    n = d_mat.shape[0]
    n_stages = max(1, math.ceil(math.log2(n)))
    if max_stages is not None:
        n_stages = min(n_stages, max(1, int(max_stages)))

    lower_coeff = xp.asarray(a_mat, dtype=b_mat.dtype).copy()
    diag_coeff = xp.asarray(d_mat, dtype=b_mat.dtype).copy()
    upper_coeff = xp.asarray(c_mat, dtype=b_mat.dtype).copy()
    rhs_work = xp.asarray(b_mat, dtype=b_mat.dtype).copy()
    return _pcr_reduce_batched(
        xp,
        lower_coeff,
        diag_coeff,
        upper_coeff,
        rhs_work,
        n_stages,
    )


def thomas_batched(xp, ab, rhs, axis: int, factors: ThomasFactors | None = None):
    """Batched tridiagonal solver along ``axis``, vectorised across batch dims.

    On GPU (CuPy) routes to ``_pcr_solve_batched`` (Parallel Cyclic Reduction):
    ceil(log₂ n) fully-vectorised stages vs 2n sequential Thomas kernel
    launches, keeping the GPU saturated throughout.

    On CPU (NumPy) uses the sequential Thomas sweep with optional pre-computed
    scalar factors for cache-efficient execution.

    Parameters
    ----------
    xp : module
        Array namespace (numpy or cupy).
    ab : (3, n) xp.ndarray
        Banded matrix in :func:`scipy.linalg.solve_banded` layout with
        ``l = u = 1``:

        ``ab[0, 1:]`` — upper diagonal  (length n-1, ab[0, 0] ignored)
        ``ab[1, :]``  — main diagonal   (length n)
        ``ab[2, :-1]`` — lower diagonal (length n-1, ab[2, -1] ignored)
    rhs : xp.ndarray
        ``rhs.shape[axis] == n``; batch shape otherwise arbitrary.
    axis : int
        Axis along which to solve.
    factors : ThomasFactors or None
        Pre-computed scalar factors (CPU path only).  Ignored on GPU where
        PCR is used regardless.

    Returns
    -------
    x : xp.ndarray
        Same shape, dtype and namespace as ``rhs``.

    Notes
    -----
    Accuracy: matches :func:`scipy.linalg.solve_banded` to FP64
    round-off (``< 1e-13`` relative on diagonally-dominant LHS).
    """
    n = rhs.shape[axis]
    validate_banded_tridiag_shape(ab, n)

    # Move target axis to front → (n, *batch)
    _, batch_shape, d = reshape_batched_rhs(xp, rhs, axis)

    # ── GPU path: Parallel Cyclic Reduction ──────────────────────────────
    if _is_cupy(xp):
        ab_dev = xp.asarray(ab)
        a_vec = xp.zeros(n, dtype=d.dtype)
        d_vec = xp.array(ab_dev[1], dtype=d.dtype)
        c_vec = xp.zeros(n, dtype=d.dtype)
        a_vec[1:] = ab_dev[2, :n - 1]
        c_vec[:n - 1] = ab_dev[0, 1:]
        x = _pcr_solve_batched(xp, a_vec, d_vec, c_vec, d)
        return restore_batched_rhs(xp, x, batch_shape, axis)

    # ── CPU path: sequential Thomas ───────────────────────────────────────
    # Allocate working storage
    d_prime = xp.empty_like(d)                     # (n, B)

    if factors is not None:
        # ── Fast path: pre-computed host scalars ─────────────────────
        cp = factors.c_prime
        di = factors.denom_inv
        lo = factors.lower

        # Forward elimination — all scalars are Python floats (no device sync)
        d_prime[0] = d[0] * di[0]
        for i in range(1, n):
            d_prime[i] = (d[i] - lo[i - 1] * d_prime[i - 1]) * di[i]

        # Back substitution
        x = xp.empty_like(d)
        x[n - 1] = d_prime[n - 1]
        for i in range(n - 2, -1, -1):
            x[i] = d_prime[i] - cp[i] * x[i + 1]
    else:
        # ── Original path: scalar recurrence on device ───────────────
        ab_dev = xp.asarray(ab)
        upper = ab_dev[0]
        main = ab_dev[1]
        lower = ab_dev[2]

        c_prime = xp.empty((n,), dtype=d.dtype)

        # Forward elimination
        c_prime[0] = upper[1] / main[0] if n > 1 else xp.asarray(0.0)
        d_prime[0] = d[0] / main[0]

        for i in range(1, n):
            denom = main[i] - lower[i - 1] * c_prime[i - 1]
            if i < n - 1:
                c_prime[i] = upper[i + 1] / denom
            d_prime[i] = (d[i] - lower[i - 1] * d_prime[i - 1]) / denom

        # Back substitution
        x = xp.empty_like(d)
        x[n - 1] = d_prime[n - 1]
        for i in range(n - 2, -1, -1):
            x[i] = d_prime[i] - c_prime[i] * x[i + 1]

    return restore_batched_rhs(xp, x, batch_shape, axis)


def tridiag_variable_batched(
    xp,
    lower,
    diag,
    upper,
    rhs,
    axis: int,
    max_stages: int | None = None,
):
    """Solve tridiagonal systems with per-line coefficients along ``axis``.

    Parameters
    ----------
    xp : module
        Array namespace (numpy or cupy).
    lower, diag, upper : xp.ndarray
        Arrays matching ``rhs.shape``.  After moving ``axis`` to the front they
        encode the lower / main / upper coefficients for every independent line.
        ``lower[0, ...]`` and ``upper[-1, ...]`` are ignored.
    rhs : xp.ndarray
        Right-hand side. ``rhs.shape[axis]`` is the system size.
    axis : int
        Axis along which to solve.
    max_stages : int, optional
        GPU only.  When provided, caps the number of PCR reduction stages.
        ``None`` keeps the exact solve with ``ceil(log2(n))`` stages.

    Returns
    -------
    x : xp.ndarray
        Same shape and namespace as ``rhs``.
    """
    if lower.shape != rhs.shape or diag.shape != rhs.shape or upper.shape != rhs.shape:
        raise ValueError("lower, diag, upper, rhs must all have the same shape")

    n = rhs.shape[axis]
    _, batch_shape, rhs_2d = reshape_batched_rhs(xp, rhs, axis)

    lower_2d = xp.moveaxis(lower, axis, 0).reshape(n, -1)
    diag_2d = xp.moveaxis(diag, axis, 0).reshape(n, -1)
    upper_2d = xp.moveaxis(upper, axis, 0).reshape(n, -1)

    if _is_cupy(xp):
        x_2d = _pcr_solve_variable_batched(
            xp,
            lower_2d,
            diag_2d,
            upper_2d,
            rhs_2d,
            max_stages=max_stages,
        )
    else:
        d_prime = xp.empty_like(rhs_2d)
        c_prime = xp.empty_like(upper_2d)

        d_prime[0] = rhs_2d[0] / diag_2d[0]
        if n > 1:
            c_prime[0] = upper_2d[0] / diag_2d[0]

        for i in range(1, n):
            denom = diag_2d[i] - lower_2d[i] * c_prime[i - 1]
            if i < n - 1:
                c_prime[i] = upper_2d[i] / denom
            d_prime[i] = (rhs_2d[i] - lower_2d[i] * d_prime[i - 1]) / denom

        x_2d = xp.empty_like(rhs_2d)
        x_2d[n - 1] = d_prime[n - 1]
        for i in range(n - 2, -1, -1):
            x_2d[i] = d_prime[i] - c_prime[i] * x_2d[i + 1]

    return restore_batched_rhs(xp, x_2d, batch_shape, axis)
