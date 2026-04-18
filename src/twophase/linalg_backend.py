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
from typing import NamedTuple


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
    a = xp.asarray(a_vec, dtype=b_mat.dtype)[:, None]
    d = xp.asarray(d_vec, dtype=b_mat.dtype)[:, None]
    c = xp.asarray(c_vec, dtype=b_mat.dtype)[:, None]
    b = b_mat.copy()

    idx = xp.arange(n)
    stride = 1
    for _ in range(n_stages):
        # Neighbour values via roll; boundary contributions are zeroed by mask.
        d_l = xp.roll(d, stride, axis=0)
        c_l = xp.roll(c, stride, axis=0)
        a_l = xp.roll(a, stride, axis=0)
        b_l = xp.roll(b, stride, axis=0)

        d_r = xp.roll(d, -stride, axis=0)
        a_r = xp.roll(a, -stride, axis=0)
        c_r = xp.roll(c, -stride, axis=0)
        b_r = xp.roll(b, -stride, axis=0)

        # α[i] = -a[i]/d[i−s], masked to 0 at left boundary.
        has_l = (idx >= stride)[:, None]
        d_l_safe = xp.where(xp.abs(d_l) > 0, d_l, 1.0)
        alpha = xp.where(has_l, -a / d_l_safe, 0.0)

        # β[i] = -c[i]/d[i+s], masked to 0 at right boundary.
        has_r = (idx < n - stride)[:, None]
        d_r_safe = xp.where(xp.abs(d_r) > 0, d_r, 1.0)
        beta = xp.where(has_r, -c / d_r_safe, 0.0)

        a = alpha * a_l
        d = d + alpha * c_l + beta * a_r
        c = beta * c_r
        b = b + alpha * b_l + beta * b_r

        stride *= 2

    return b / d


class ThomasFactors(NamedTuple):
    """Pre-computed scalar recurrence for a tridiagonal matrix.

    Fields are host (Python float) arrays so that the GPU solve loop
    never reads scalar elements from device memory.
    """
    c_prime: list[float]    # length n, c_prime[n-1] = 0
    denom_inv: list[float]  # length n, 1 / denom[i]
    lower: list[float]      # length n, lower[0] unused


def thomas_precompute(ab) -> ThomasFactors:
    """Pre-compute the scalar recurrence from a banded matrix.

    Parameters
    ----------
    ab : array-like, shape (3, n)
        Banded matrix (same layout as ``thomas_batched``).
        If on GPU, a small (3n float) D2H transfer is performed once.

    Returns
    -------
    ThomasFactors
        Pre-computed factors for ``thomas_batched(..., factors=...)``.
    """
    import numpy as np_host

    # Pull to host if needed (small 3×n array).
    ab_h = np_host.asarray(ab) if not isinstance(ab, np_host.ndarray) else ab
    ab_h = ab_h.astype(np_host.float64, copy=False)

    n = ab_h.shape[1]
    upper = ab_h[0]   # upper[0] unused
    main = ab_h[1]
    lower = ab_h[2]   # lower[-1] unused

    c_prime = [0.0] * n
    denom_inv = [0.0] * n

    # i = 0
    denom_inv[0] = 1.0 / float(main[0])
    if n > 1:
        c_prime[0] = float(upper[1]) * denom_inv[0]

    # i = 1 .. n-1
    for i in range(1, n):
        denom = float(main[i]) - float(lower[i - 1]) * c_prime[i - 1]
        denom_inv[i] = 1.0 / denom
        if i < n - 1:
            c_prime[i] = float(upper[i + 1]) * denom_inv[i]

    lower_h = [float(lower[i]) for i in range(n)]

    return ThomasFactors(c_prime=c_prime, denom_inv=denom_inv, lower=lower_h)


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
    if ab.shape[0] != 3 or ab.shape[1] != n:
        raise ValueError(
            f"ab must have shape (3, n={n}); got {tuple(ab.shape)}"
        )

    # Move target axis to front → (n, *batch)
    moved = xp.moveaxis(rhs, axis, 0)
    batch_shape = moved.shape[1:]
    d = moved.reshape(n, -1)                       # (n, B)

    # ── GPU path: Parallel Cyclic Reduction ──────────────────────────────
    if _is_cupy(xp):
        ab_dev = xp.asarray(ab)
        a_vec = xp.zeros(n, dtype=d.dtype)
        d_vec = xp.array(ab_dev[1], dtype=d.dtype)
        c_vec = xp.zeros(n, dtype=d.dtype)
        a_vec[1:] = ab_dev[2, :n - 1]
        c_vec[:n - 1] = ab_dev[0, 1:]
        x = _pcr_solve_batched(xp, a_vec, d_vec, c_vec, d)
        x_moved = x.reshape((n,) + batch_shape)
        return xp.moveaxis(x_moved, 0, axis)

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

    x_moved = x.reshape((n,) + batch_shape)
    return xp.moveaxis(x_moved, 0, axis)
