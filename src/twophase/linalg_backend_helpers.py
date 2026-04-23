"""Helper utilities for backend-agnostic tridiagonal solves."""

from __future__ import annotations

from typing import NamedTuple


class ThomasFactors(NamedTuple):
    """Pre-computed scalar recurrence for a tridiagonal matrix."""

    c_prime: list[float]
    denom_inv: list[float]
    lower: list[float]


def validate_banded_tridiag_shape(ab, n: int) -> None:
    """Validate a banded `(3, n)` tridiagonal matrix shape."""
    if ab.shape[0] != 3 or ab.shape[1] != n:
        raise ValueError(f"ab must have shape (3, n={n}); got {tuple(ab.shape)}")


def reshape_batched_rhs(xp, rhs, axis: int):
    """Move the solve axis to the front and flatten batch dimensions."""
    moved = xp.moveaxis(rhs, axis, 0)
    batch_shape = moved.shape[1:]
    return moved, batch_shape, moved.reshape(moved.shape[0], -1)


def restore_batched_rhs(xp, x, batch_shape, axis: int):
    """Restore a flattened batched solve result to the original axis layout."""
    x_moved = x.reshape((x.shape[0],) + batch_shape)
    return xp.moveaxis(x_moved, 0, axis)


def thomas_precompute(ab) -> ThomasFactors:
    """Pre-compute the scalar recurrence from a banded matrix."""
    import numpy as np_host

    getter = getattr(ab, "get", None)
    if callable(getter):
        ab_h = getter()
    else:
        ab_h = np_host.asarray(ab) if not isinstance(ab, np_host.ndarray) else ab
    ab_h = ab_h.astype(np_host.float64, copy=False)

    n = ab_h.shape[1]
    upper = ab_h[0]
    main = ab_h[1]
    lower = ab_h[2]

    c_prime = [0.0] * n
    denom_inv = [0.0] * n

    denom_inv[0] = 1.0 / float(main[0])
    if n > 1:
        c_prime[0] = float(upper[1]) * denom_inv[0]

    for i in range(1, n):
        denom = float(main[i]) - float(lower[i - 1]) * c_prime[i - 1]
        denom_inv[i] = 1.0 / denom
        if i < n - 1:
            c_prime[i] = float(upper[i + 1]) * denom_inv[i]

    return ThomasFactors(
        c_prime=c_prime,
        denom_inv=denom_inv,
        lower=[float(lower[i]) for i in range(n)],
    )
