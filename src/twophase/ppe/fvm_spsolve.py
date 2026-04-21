"""PPESolverFVMSpsolve: FVM-based PPE solver via sparse direct solve.

Wraps PPEBuilder + scipy.sparse.linalg.spsolve, adapting the legacy
TwoPhaseNSSolver._solve_ppe() path to the IPPESolver interface.

This is a PR-1 violation (FVM instead of CCD), but is the mandatory path
for ch12/ch13 integration per PR-2. See PPEBuilder docstring for rationale.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np

from .interfaces import IPPESolver
from .ppe_builder import PPEBuilder

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid
    from ..core.boundary import BoundarySpec


class PPESolverFVMSpsolve(IPPESolver):
    """FVM Poisson solver via sparse direct solve (scipy.sparse.linalg.spsolve).

    NS role
    -------
    Solves the variable-density PPE at Step 6 (§9.1 algorithm):

        ∇·[(1/ρ̃) ∇p] = (1/Δt) ∇·u*

    so that Step 7 corrector recovers divergence-free velocity:

        u^{n+1} = u* − (Δt/ρ̃) ∇p^{n+1}

    Discretisation: FVM O(h²) harmonic-mean face coefficients.
    Mandatory for ch12+ (PR-2/PR-6).

    Implements the legacy TwoPhaseNSSolver._solve_ppe() path as an IPPESolver.
    Suitable for ch12+ integration; not for ch11 smooth RHS (use PPESolverCCDLU instead).

    Parameters
    ----------
    backend : Backend
        Array namespace (CPU/GPU)
    grid : Grid
        Computational grid
    bc_type : str
        'wall' (Neumann) or 'periodic'
    bc_spec : BoundarySpec, optional
        For explicit pin DOF specification
    """

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        bc_type: str = "wall",
        bc_spec: "BoundarySpec | None" = None,
    ):
        self.backend = backend
        self.xp = backend.xp
        self.ppb = PPEBuilder(backend, grid, bc_type, bc_spec)

        # Pre-compute sparse structure (CSR row/col indices) once
        # This avoids rebuilding on every solve when only values change
        import scipy.sparse as sp
        dummy_rho = np.ones(grid.shape, dtype=np.float64)
        triplet, shape = self.ppb.build(dummy_rho)
        self._ppe_struct_rows = triplet[1]  # row indices
        self._ppe_struct_cols = triplet[2]  # col indices

    def solve(self, rhs: np.ndarray, rho: np.ndarray, dt: float = 0.0, p_init=None) -> np.ndarray:
        """Solve the variable-density PPE via sparse FVM + direct solve.

        Parameters
        ----------
        rhs : array, shape grid.shape
            Divergence RHS (source term)
        rho : array, shape grid.shape
            Density field (defines variable coefficients)
        dt : float
            Timestep (unused in this direct solver; kept for interface compatibility)
        p_init : array, optional
            Initial guess (ignored by direct solve; kept for interface compatibility)

        Returns
        -------
        p : array, shape grid.shape
            Pressure correction field
        """
        import scipy.sparse as sp
        xp = self.xp
        n = self.ppb.n_dof

        # Flatten and zero the pinned DOF (gauge freedom)
        rhs_vec = xp.asarray(rhs).ravel().copy()
        rhs_vec[self.ppb._pin_dof] = 0.0

        # Build sparse matrix (only values; structure is pre-computed)
        data = self.ppb.build_values(rho)

        if self.backend.is_gpu():
            # GPU path: use device-side CSR matrix and solver
            A = self.backend.sparse.csr_matrix(
                (data, (self._ppe_struct_rows, self._ppe_struct_cols)), shape=(n, n)
            )
            p_vec = self.backend.sparse_linalg.spsolve(A, rhs_vec)
            return p_vec.reshape(rho.shape)

        # CPU path: move to host for scipy.sparse.linalg.spsolve
        A = sp.csr_matrix(
            (data, (self._ppe_struct_rows, self._ppe_struct_cols)), shape=(n, n)
        )
        rhs_host = np.asarray(self.backend.to_host(rhs_vec))
        p_host = self.backend.sparse_linalg.spsolve(A, rhs_host)
        return xp.asarray(p_host.reshape(rho.shape))

    def get_matrix(self, rho: np.ndarray) -> "sp.csr_matrix":
        """Build and return the full sparse CSR matrix (for diagnostics/IIM).

        Parameters
        ----------
        rho : array, shape grid.shape
            Density field

        Returns
        -------
        A : scipy.sparse.csr_matrix
            Variable-coefficient Laplacian matrix
        """
        import scipy.sparse as sp
        triplet, shape = self.ppb.build(rho)
        return sp.csr_matrix(
            (triplet[0], (triplet[1], triplet[2])), shape=shape
        )
