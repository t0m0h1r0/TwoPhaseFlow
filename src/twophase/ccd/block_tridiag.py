"""
Block-tridiagonal LU solver.

Solves the system

    D_1 x_1 + U_1 x_2                           = b_1
    L_2 x_1 + D_2 x_2 + U_2 x_3                = b_2
    ...
    L_{n-1} x_{n-2} + D_{n-1} x_{n-1}          = b_{n-1}

where every block D_i, L_i, U_i is a (2×2) matrix and b_i, x_i are
length-2 vectors.  Batch processing allows solving many independent
right-hand sides simultaneously.

The factorisation is performed once (``factorize``); the back-substitution
(``solve``) is called at every time step.

This module is used exclusively by :class:`twophase.ccd.ccd_solver.CCDSolver`.
"""

from __future__ import annotations
import numpy as np
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class BlockTridiagSolver:
    """LU-factorised block-tridiagonal solver (2×2 blocks).

    Parameters
    ----------
    xp : array namespace (numpy or cupy)
    """

    def __init__(self, xp):
        self.xp = xp
        self._factorised = False

    # ── Factorisation ─────────────────────────────────────────────────────

    def factorize(
        self,
        diag: List[np.ndarray],
        lower: List[np.ndarray],
        upper: List[np.ndarray],
    ) -> None:
        """LU-factorise the block-tridiagonal matrix.

        Parameters
        ----------
        diag  : list of n   (2,2) arrays — diagonal blocks D_1 … D_n
        lower : list of n   (2,2) arrays — sub-diagonal blocks L_1 … L_n
                (L_1 is unused / zero)
        upper : list of n   (2,2) arrays — super-diagonal blocks U_1 … U_n
                (U_n is unused / zero)

        Notes
        -----
        Factorisation runs on the host in numpy (the blocks are 2×2 and
        numerically sensitive — use LAPACK double precision regardless of
        backend). The resulting factors are then transferred once to the
        active device so that subsequent :meth:`solve` calls do not incur
        per-iteration host→device copies.
        """
        n = len(diag)
        assert len(lower) == n and len(upper) == n

        LU = [None] * n         # modified diagonal (LU factors)
        L_store = [None] * n    # L_i * D_{i-1}^{-1}
        U_store = [upper[i].copy() for i in range(n)]

        LU[0] = diag[0].copy()
        for i in range(1, n):
            # L_store[i] = lower[i] @ inv(LU[i-1])
            try:
                Linv = np.linalg.solve(LU[i - 1].T, lower[i].T).T
            except np.linalg.LinAlgError:
                # Fallback: pseudo-inverse
                Linv = lower[i] @ np.linalg.pinv(LU[i - 1])
            L_store[i] = Linv
            LU[i] = diag[i] - Linv @ U_store[i - 1]

        # Stack into (n, 2, 2) host arrays. L_store[0] is unused by solve();
        # fill with zeros so indexing is uniform.
        zero22 = np.zeros((2, 2))
        L_stack = np.stack([L_store[i] if L_store[i] is not None else zero22
                            for i in range(n)])
        U_stack = np.stack(U_store)
        LU_stack = np.stack(LU)

        # Transfer once to the active device.
        xp = self.xp
        self._n = n
        self._LU_dev = xp.asarray(LU_stack)
        self._L_dev = xp.asarray(L_stack)
        self._U_dev = xp.asarray(U_stack)
        self._factorised = True

    # ── Solve ─────────────────────────────────────────────────────────────

    def solve(self, rhs: np.ndarray) -> np.ndarray:
        """Solve the block-tridiagonal system for batched RHS.

        Parameters
        ----------
        rhs : array of shape ``(n, 2, batch)``

        Returns
        -------
        x : array of shape ``(n, 2, batch)``
        """
        assert self._factorised, "Call factorize() first"
        xp = self.xp
        n = self._n
        rhs = xp.asarray(rhs)

        x = xp.zeros_like(rhs)

        # ── Forward substitution (L-solve) ────────────────────────────────
        # y_1 = b_1
        # y_i = b_i - L_store[i] @ y_{i-1}
        y = xp.zeros_like(rhs)
        y[0] = rhs[0]
        for i in range(1, n):
            L = self._L_dev[i]   # (2, 2) on device
            # L @ y[i-1]: (2,2) × (2,batch) → (2,batch)
            y[i] = rhs[i] - xp.tensordot(L, y[i - 1], axes=([1], [0]))

        # ── Back substitution (U-solve) ───────────────────────────────────
        # x_{n} = LU[n]^{-1} y_{n}
        # x_i   = LU[i]^{-1} (y_i - U_store[i] @ x_{i+1})
        x[n - 1] = _solve2x2_batch(xp, self._LU_dev[n - 1], y[n - 1])
        for i in range(n - 2, -1, -1):
            rhs_i = y[i] - xp.tensordot(self._U_dev[i], x[i + 1], axes=([1], [0]))
            x[i] = _solve2x2_batch(xp, self._LU_dev[i], rhs_i)

        return x


# ── Helper ────────────────────────────────────────────────────────────────

def _solve2x2_batch(xp, A, b):
    """Solve A x = b where A is (2,2) and b is (2, batch).

    ``A`` may live on the same device as ``b`` (numpy or cupy) — no
    cross-namespace conversions are performed.

    Uses explicit Cramer's rule to avoid per-sample linalg.solve overhead.
    """
    a00 = A[0, 0]; a01 = A[0, 1]
    a10 = A[1, 0]; a11 = A[1, 1]
    det = a00 * a11 - a01 * a10
    # Guard against near-singular (shouldn't happen with CCD coefficients)
    det = xp.where(xp.abs(det) < 1e-300,
                   xp.sign(det) * 1e-300, det)
    inv_det = 1.0 / det
    x = xp.empty_like(b)
    x[0] = inv_det * (a11 * b[0] - a01 * b[1])
    x[1] = inv_det * (a00 * b[1] - a10 * b[0])
    return x
