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


class PPEBuilder:
    """Build and update the sparse PPE matrix A.

    Parameters
    ----------
    backend : Backend
    grid    : Grid
    """

    def __init__(self, backend: "Backend", grid: "Grid"):
        self.backend = backend
        self.xp = backend.xp
        self.grid = grid
        self.ndim = grid.ndim
        self.N = grid.N
        self.shape_field = grid.shape   # (Nx+1, Ny+1[, Nz+1])

        # Total degrees of freedom = number of grid nodes
        self.n_dof = int(np.prod(self.shape_field))

        # Pre-compute static index arrays for vectorised assembly
        self._build_index_arrays()

    # ── Public API ────────────────────────────────────────────────────────

    def build(self, rho) -> tuple:
        """Build the sparse PPE matrix for the given density field.

        Parameters
        ----------
        rho : array, shape ``grid.shape``

        Returns
        -------
        (data, row, col) : CSR triplet arrays (on host, scipy-compatible)
        A_shape : (n_dof, n_dof)
        """
        import numpy as np_host

        rho_host = self.backend.to_host(rho)
        n = self.n_dof
        ndim = self.ndim

        # Accumulate COO triplets
        data_list = []
        row_list  = []
        col_list  = []

        for ax in range(ndim):
            h = float(self.grid.L[ax] / self.grid.N[ax])
            h2 = h * h
            N_ax = self.N[ax]
            field_shape = self.shape_field

            # Indices of all interior faces along ax
            # Face i+½ between nodes i and i+1 in axis ax
            idx_L, idx_R = self._face_indices[ax]  # flat node indices

            rho_L = rho_host.ravel()[idx_L]
            rho_R = rho_host.ravel()[idx_R]
            a_f = 2.0 / (rho_L + rho_R)   # harmonic mean face coefficient

            # Off-diagonal entries: node L ↔ node R
            # A[L, R] += a_f / h²  and  A[R, L] += a_f / h²
            coeff = a_f / h2

            # L → R contribution
            data_list.append(coeff)
            row_list.append(idx_L)
            col_list.append(idx_R)

            # R → L contribution
            data_list.append(coeff)
            row_list.append(idx_R)
            col_list.append(idx_L)

            # Diagonal contributions: A[L,L] -= coeff, A[R,R] -= coeff
            data_list.append(-coeff)
            row_list.append(idx_L)
            col_list.append(idx_L)

            data_list.append(-coeff)
            row_list.append(idx_R)
            col_list.append(idx_R)

        data = np_host.concatenate(data_list)
        rows = np_host.concatenate(row_list)
        cols = np_host.concatenate(col_list)

        # Pin one pressure degree of freedom (node 0) to fix the null space
        # p[0] = 0  →  clear row 0 and set diagonal to 1
        mask = rows != 0
        data = data[mask]
        rows = rows[mask]
        cols = cols[mask]

        # Add A[0,0] = 1
        data = np_host.append(data, 1.0)
        rows = np_host.append(rows, 0)
        cols = np_host.append(cols, 0)

        return (data, rows, cols), (n, n)

    # ── Index array pre-computation ───────────────────────────────────────

    def _build_index_arrays(self) -> None:
        """Pre-compute the flat node indices of each interior face."""
        import numpy as np_host
        self._face_indices = {}

        shape = self.shape_field  # e.g. (Nx+1, Ny+1)

        for ax in range(self.ndim):
            # Build a multi-dimensional grid of node indices
            ranges = [np_host.arange(s) for s in shape]

            # For axis ax, L nodes run from 0 to N[ax]-1,
            # R nodes run from 1 to N[ax]  (internal faces only)
            N_ax = self.N[ax]

            # Left node indices: all i[ax] in 0..N[ax]-1
            ranges_L = [r.copy() for r in ranges]
            ranges_L[ax] = np_host.arange(0, N_ax)   # excludes boundary face

            # Right node indices: i[ax] + 1
            ranges_R = [r.copy() for r in ranges]
            ranges_R[ax] = np_host.arange(1, N_ax + 1)

            grid_L = np_host.meshgrid(*ranges_L, indexing='ij')
            grid_R = np_host.meshgrid(*ranges_R, indexing='ij')

            # Flat indices via np.ravel_multi_index
            idx_L = np_host.ravel_multi_index(
                [g.ravel() for g in grid_L], shape
            )
            idx_R = np_host.ravel_multi_index(
                [g.ravel() for g in grid_R], shape
            )

            self._face_indices[ax] = (idx_L, idx_R)
