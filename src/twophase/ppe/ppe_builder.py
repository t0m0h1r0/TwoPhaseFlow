"""
Variable-density Pressure Poisson Equation (PPE) matrix builder.

Implements §7.3 (Eq. 62–63) of the paper.

The PPE for the variable-density projection method is (§7.1 Eq. 57):

    ∇·[(1/ρ̃) ∇p] = (1/Δt) ∇·u*_RC                      (§7.1 Eq. 57)

FVM discretisation on a uniform grid gives the 5-point (2-D) or 7-point
(3-D) stencil with face coefficients (§7.3 Eq. 63):

    a_{i+½} = 2 / (ρ_i + ρ_{i+1})     (harmonic mean of 1/ρ)

The discrete equation at cell (i,j) in 2-D:

    a_{i+½}(p_{i+1,j}−p_{i,j})/h² − (a_{i+½}+a_{i−½})p_{i,j}/h²
  + a_{i−½}(p_{i−1,j}−p_{i,j})/h²
  + [y-direction terms] = rhs_{i,j}

Assembled as a sparse CSR matrix via vectorised NumPy/CuPy indexing
(no Python for-loops over cells, fixing Known Issue #1).

Boundary conditions:
  Wall (Neumann ∂p/∂n = 0): ghost-cell cancellation → omit face term.
  Dirichlet (p = 0 at one corner): pin one degree of freedom.
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid
    from ..core.boundary import BoundarySpec

from .ppe_builder_helpers import (
    build_ppe_index_arrays,
    build_ppe_matrix_triplets,
    prepare_ppe_rhs_vector,
)


# DO NOT DELETE — passed tests 2026-03-20
# Superseded by: _CCDPPEBase._build_sparse_operator() in ccd_ppe_base.py
# Retained for: ch12+ integration (PPESolverFVMSpsolve per PR-2)
# Note: PR-1 (CCD Primacy) is superseded by PR-2 (variable-density FVM for ch12+)
class PPEBuilder:
    """FVM sparse PPE matrix builder for ch12+ integration.

    FVM O(h²) finite-difference Laplacian matrix assembly. Used by
    PPESolverFVMSpsolve for non-uniform variable-density integration
    where CCD Kronecker assembly is unavailable. Per PROJECT_RULES PR-2,
    this is the mandate approach for ch12/ch13 experiments; CCD solvers
    remain the default for ch11 component tests.

    Parameters
    ----------
    backend : Backend
    grid    : Grid
    bc_type : 'wall' (Neumann) or 'periodic'
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
        self.grid = grid
        self.ndim = grid.ndim
        self.N = grid.N
        self.shape_field = grid.shape   # (Nx+1, Ny+1[, Nz+1])
        self.bc_type = bc_type

        # Total degrees of freedom = number of grid nodes
        self.n_dof = int(np.prod(self.shape_field))

        # Pressure gauge pin DOF (via BoundarySpec).
        if bc_spec is not None:
            self._pin_dof = bc_spec.pin_dof
        elif bc_type == 'wall':
            centre_idx = tuple(n // 2 for n in self.N)
            self._pin_dof = int(np.ravel_multi_index(centre_idx, self.shape_field))
        else:
            self._pin_dof = 0

        # Pre-compute static index arrays for vectorised assembly
        self._build_index_arrays()

        # GPU acceleration (build_values_xp): lazily populated on first call.
        self._face_indices_dev: dict = {}   # {ax: (idx_L_dev, idx_R_dev)}
        self._gpu_coeff_cache: dict = {}    # static device arrays (BC masks, non-uniform coeff)

    # ── Public API ────────────────────────────────────────────────────────

    def build(self, rho) -> tuple:
        """Build the sparse PPE matrix COO triplets for the given density field.

        Unified xp implementation: works for both NumPy (CPU) and CuPy (GPU)
        with the same code path — no separate GPU method required.
        Static face-index arrays are lazily converted to xp on first call
        and cached in _face_indices_dev / _gpu_coeff_cache.

        Parameters
        ----------
        rho : array, shape ``grid.shape`` (any device; xp.asarray is applied)

        Returns
        -------
        (data, rows, cols) : xp.ndarray  COO triplets (on device when GPU)
        A_shape : (n_dof, n_dof)

        Note
        ----
        Periodic BC uses np.isin (not in CuPy): rows are pulled to host
        for that one mask operation, then results converted back to xp.
        """
        return build_ppe_matrix_triplets(self, rho)

    def build_structure(self):
        """Return the fixed sparsity pattern (rows, cols) and metadata.

        The sparsity pattern depends only on grid topology and boundary
        conditions — it does NOT change with ρ.  Call once at init time.

        Returns
        -------
        rows, cols : np.ndarray (int)
            COO row/column indices (same ordering as ``build_values``).
        n_dof : int
        """
        import numpy as np_host

        # Use a dummy uniform-density field to extract the structural indices.
        rho_dummy = np_host.ones(self.shape_field)
        (_data, rows, cols), _shape = self.build(rho_dummy)
        # Cache the mask/pin structure for build_values.
        self._struct_rows = rows
        self._struct_cols = cols
        self._struct_nnz = len(rows)
        return rows, cols, self.n_dof

    def build_values(self, rho):
        """Re-compute only the coefficient values for a new density field.

        Must call ``build_structure()`` first. Returns the data vector
        in the same COO ordering as the cached structure arrays.
        When the backend is GPU, returns a device (CuPy) array — no D2H of rho.

        Parameters
        ----------
        rho : array, shape ``grid.shape`` (any device; xp.asarray applied)

        Returns
        -------
        data : xp.ndarray, shape (nnz,)
        """
        (data, _rows, _cols), _shape = self.build(rho)
        return data

    def invalidate_gpu_cache(self):
        """Clear cached device arrays (call after grid rebuild)."""
        self._face_indices_dev.clear()
        self._gpu_coeff_cache.clear()

    def prepare_rhs(self, rhs_field):
        """Prepare the RHS vector for the PPE solve.

        Zeros the pin DOF and (for periodic BC) all ghost-node DOFs.
        Returns a flat 1-D array suitable for ``spsolve(A, rhs_vec)``.

        Parameters
        ----------
        rhs_field : array, shape ``grid.shape``

        Returns
        -------
        rhs_vec : np.ndarray, shape (n_dof,)
        """
        return prepare_ppe_rhs_vector(self, rhs_field)

    # ── Index array pre-computation ───────────────────────────────────────

    def _build_index_arrays(self) -> None:
        """Pre-compute the flat node indices of each face type."""
        build_ppe_index_arrays(self)
