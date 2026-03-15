"""
MINRES PPE solver with warm-start (pseudo-time Krylov variant).

Implements a matrix-free-compatible pseudo-time approach for the PPE:

    ∇·(1/ρ ∇p) = q_h,    q_h = (1/Δt) ∇·u*_RC

using scipy MINRES on the same FVM sparse system as PPESolver, but with:

  * Symmetric Dirichlet pinning (row AND column 0 zeroed), making the
    matrix truly symmetric so that MINRES (not BiCGSTAB) can be used.
  * Warm-start from p^n, drastically reducing iteration count when
    the solution changes slowly between time steps.

Why MINRES instead of BiCGSTAB?
  MINRES is optimal for symmetric indefinite systems (a superset of the
  symmetric positive definite case handled by CG).  After symmetric
  pinning the FVM Laplacian is symmetric and negative semi-definite on
  the interior, so MINRES is the mathematically correct Krylov choice.

Usage difference from PPESolver:
  PPESolver  – builds sparse matrix, solves with BiCGSTAB, no warm-start.
  This class – builds sparse matrix, solves with MINRES, warm-starts from
               previous p.
"""

from __future__ import annotations
import warnings
import numpy as np
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver


class PPESolverPseudoTime:
    """MINRES solver for the variable-density PPE with warm-start.

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig  (uses pseudo_tol, pseudo_maxiter)
    grid    : Grid
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
    ) -> None:
        self.xp = backend.xp
        self.backend = backend
        self.ndim = grid.ndim
        self.grid = grid
        self.tol = config.pseudo_tol
        self.maxiter = config.pseudo_maxiter

        # Pre-compute static face-index arrays (same logic as PPEBuilder)
        self._face_indices: dict = {}
        self._build_index_arrays()

    # ── Public API ────────────────────────────────────────────────────────

    def solve(
        self,
        p_init,
        q_h,
        rho,
        ccd: "CCDSolver",   # accepted for API compatibility, not used here
    ):
        """Solve ∇·(1/ρ ∇p) = q_h using MINRES with warm-start from p_init.

        Parameters
        ----------
        p_init : array, shape ``grid.shape``  — warm-start (use p^n)
        q_h    : array, shape ``grid.shape``  — RHS = (1/Δt) ∇·u*_RC
        rho    : array, shape ``grid.shape``  — density field
        ccd    : CCDSolver  (not used; present for interface compatibility)

        Returns
        -------
        p : array, shape ``grid.shape``
        """
        import scipy.sparse as sp
        import scipy.sparse.linalg as spla

        rho_h = np.asarray(self.backend.to_host(rho), dtype=float)
        q_h_host = np.asarray(self.backend.to_host(q_h), dtype=float).ravel()
        p0_host = np.asarray(self.backend.to_host(p_init), dtype=float).ravel()

        # Build sparse FVM matrix with SYMMETRIC pinning
        (data, rows, cols), A_shape = self._build_sym(rho_h)
        A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)

        # Consistent RHS: pin p[0] = 0
        q_h_host[0] = 0.0

        p_flat, info = spla.minres(
            A,
            q_h_host,
            x0=p0_host,
            rtol=self.tol,
            maxiter=self.maxiter,
        )

        if info != 0:
            warnings.warn(
                f"PPE MINRES did not converge (info={info}). "
                "Consider increasing pseudo_maxiter or loosening pseudo_tol.",
                RuntimeWarning,
                stacklevel=2,
            )

        p_arr = p_flat.reshape(self.grid.shape)
        return self.backend.to_device(p_arr)

    # ── Matrix assembly ───────────────────────────────────────────────────

    def _build_sym(self, rho: np.ndarray) -> Tuple:
        """Build the FVM PPE matrix with SYMMETRIC pinning of node 0.

        Symmetric pinning:  A[0, :] = A[:, 0] = e_0  (identity row+col).
        This preserves symmetry so MINRES can be used.
        """
        n = int(np.prod(self.grid.shape))
        ndim = self.ndim
        data_list, row_list, col_list = [], [], []

        for ax in range(ndim):
            h = float(self.grid.L[ax] / self.grid.N[ax])
            h2 = h * h
            idx_L, idx_R = self._face_indices[ax]

            rho_L = rho.ravel()[idx_L]
            rho_R = rho.ravel()[idx_R]
            a_f = 2.0 / (rho_L + rho_R)
            coeff = a_f / h2

            # Off-diagonal: L↔R connections (symmetric)
            for (src, dst) in [(idx_L, idx_R), (idx_R, idx_L)]:
                data_list.append(coeff)
                row_list.append(src)
                col_list.append(dst)

            # Diagonal contributions: subtract coeff at both ends
            for idx in [idx_L, idx_R]:
                data_list.append(-coeff)
                row_list.append(idx)
                col_list.append(idx)

        data = np.concatenate(data_list)
        rows = np.concatenate(row_list)
        cols = np.concatenate(col_list)

        # Symmetric pinning of node 0:
        # Remove ALL entries in row 0 AND column 0, then add A[0,0] = 1.
        mask = (rows != 0) & (cols != 0)
        data = data[mask]
        rows = rows[mask]
        cols = cols[mask]

        data = np.append(data, 1.0)
        rows = np.append(rows, 0)
        cols = np.append(cols, 0)

        return (data, rows, cols), (n, n)

    # ── Index array pre-computation ───────────────────────────────────────

    def _build_index_arrays(self) -> None:
        """Pre-compute flat node indices of interior faces (same as PPEBuilder)."""
        shape = self.grid.shape

        for ax in range(self.ndim):
            ranges = [np.arange(s) for s in shape]
            N_ax = self.grid.N[ax]

            ranges_L = [r.copy() for r in ranges]
            ranges_L[ax] = np.arange(0, N_ax)

            ranges_R = [r.copy() for r in ranges]
            ranges_R[ax] = np.arange(1, N_ax + 1)

            grid_L = np.meshgrid(*ranges_L, indexing='ij')
            grid_R = np.meshgrid(*ranges_R, indexing='ij')

            idx_L = np.ravel_multi_index([g.ravel() for g in grid_L], shape)
            idx_R = np.ravel_multi_index([g.ravel() for g in grid_R], shape)
            self._face_indices[ax] = (idx_L, idx_R)
