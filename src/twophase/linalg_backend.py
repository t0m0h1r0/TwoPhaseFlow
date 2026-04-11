"""
Backend-agnostic linear algebra helpers.

Hosts the one numerical routine that does not have a direct ``cupyx``
equivalent: a batched tridiagonal (Thomas) solver used by the compact
filters in :mod:`twophase.levelset.compact_filters`.

The algorithm is the textbook Thomas sweep (forward elimination +
back substitution) parallelised across *all batch dimensions* of the
right-hand side. The target axis is moved to position 0 so a single
Python loop of length ``n`` can issue one vectorised kernel per
iteration; the cost is ``2n`` kernel launches per call, which is
acceptable for ``n <= 256`` typical of compact-filter passes.

Stability
---------
Unpivoted Thomas is stable iff the tridiagonal matrix is diagonally
dominant. The only consumers (Helmholtz-κ and Lele/Kim Padé filters)
build *diagonally dominant* LHS matrices by construction, so no
pivoting is required. Do not use ``thomas_batched`` on general banded
systems.
"""

from __future__ import annotations


def thomas_batched(xp, ab, rhs, axis: int):
    """Sequential Thomas sweep along ``axis``, vectorised across batch dims.

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

    # Ensure ab is on the same device as rhs
    ab_dev = xp.asarray(ab)
    upper = ab_dev[0]                              # (n,)  upper[0] unused
    main  = ab_dev[1]                              # (n,)
    lower = ab_dev[2]                              # (n,)  lower[-1] unused

    # Allocate working storage on device
    c_prime = xp.empty((n,), dtype=d.dtype)
    d_prime = xp.empty_like(d)                     # (n, B)

    # ── Forward elimination ──────────────────────────────────────────
    # i = 0
    c_prime[0] = upper[1] / main[0] if n > 1 else xp.asarray(0.0)
    d_prime[0] = d[0] / main[0]

    # i = 1 .. n-1
    for i in range(1, n):
        denom = main[i] - lower[i - 1] * c_prime[i - 1]
        if i < n - 1:
            c_prime[i] = upper[i + 1] / denom
        d_prime[i] = (d[i] - lower[i - 1] * d_prime[i - 1]) / denom

    # ── Back substitution ────────────────────────────────────────────
    x = xp.empty_like(d)                           # (n, B)
    x[n - 1] = d_prime[n - 1]
    for i in range(n - 2, -1, -1):
        x[i] = d_prime[i] - c_prime[i] * x[i + 1]

    x_moved = x.reshape((n,) + batch_shape)
    return xp.moveaxis(x_moved, 0, axis)
