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


# DO NOT DELETE — passed tests 2026-03-20
# Superseded by: _CCDPPEBase._build_sparse_operator() in ccd_ppe_base.py
# Retained for: FVM reference (used by legacy PPESolver, PPESolverLU)
# Violation: PR-1 (FVM O(h²), not CCD)
class PPEBuilder:
    """FVM sparse PPE matrix builder. Legacy — CCD solvers use Kronecker assembly.

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

        # Strides for extracting per-axis indices from flat indices (C/ij order)
        strides = [int(np_host.prod(self.shape_field[ax + 1:]))
                   for ax in range(ndim)]

        for ax in range(ndim):
            N_ax = self.N[ax]
            idx_L, idx_R = self._face_indices[ax]  # flat node indices

            rho_L = rho_host.ravel()[idx_L]
            rho_R = rho_host.ravel()[idx_R]
            a_f = 2.0 / (rho_L + rho_R)   # harmonic mean face coefficient

            if not self.grid.uniform:
                # Non-uniform grid: per-face local spacings from grid.coords.
                # Face between node k and k+1:
                #   d_face[k] = x[k+1] − x[k]  (gradient denominator)
                #   dv[i] = control volume width at node i:
                #     boundary: (x[1]−x[0])/2 or (x[N]−x[N-1])/2
                #     interior: (x[i+1]−x[i-1])/2
                coords = np_host.asarray(self.grid.coords[ax])
                d_face = coords[1:] - coords[:-1]          # (N_ax,) face widths
                dv = np_host.empty(len(coords))
                dv[0]    = (coords[1] - coords[0]) / 2.0
                dv[-1]   = (coords[-1] - coords[-2]) / 2.0
                dv[1:-1] = (coords[2:] - coords[:-2]) / 2.0

                stride = strides[ax]
                ax_idx_L = (idx_L // stride) % self.shape_field[ax]
                ax_idx_R = (idx_R // stride) % self.shape_field[ax]
                d_f  = d_face[ax_idx_L]    # face width for this face
                dv_L = dv[ax_idx_L]         # control volume of left node
                dv_R = dv[ax_idx_R]         # control volume of right node

                # Face flux coefficient: a_f / d_face, divided by control volume
                coeff_for_L = a_f / d_f / dv_L
                coeff_for_R = a_f / d_f / dv_R
            else:
                h = float(self.grid.L[ax] / N_ax)
                h2 = h * h
                coeff = a_f / h2

                if self.bc_type == 'periodic':
                    coeff_for_L = coeff
                    coeff_for_R = coeff
                else:
                    # Node-centred boundary correction:
                    # Boundary nodes have control volume h/2 → coefficient doubles.
                    stride = strides[ax]
                    ax_idx_L = (idx_L // stride) % self.shape_field[ax]
                    ax_idx_R = (idx_R // stride) % self.shape_field[ax]
                    coeff_for_L = np_host.where(ax_idx_L == 0,    2.0 * coeff, coeff)
                    coeff_for_R = np_host.where(ax_idx_R == N_ax, 2.0 * coeff, coeff)

            # L → R contribution (enters L's equation row)
            data_list.append(coeff_for_L)
            row_list.append(idx_L)
            col_list.append(idx_R)

            # R → L contribution (enters R's equation row)
            data_list.append(coeff_for_R)
            row_list.append(idx_R)
            col_list.append(idx_L)

            # Diagonal contributions: A[L,L] -= coeff_for_L, A[R,R] -= coeff_for_R
            data_list.append(-coeff_for_L)
            row_list.append(idx_L)
            col_list.append(idx_L)

            data_list.append(-coeff_for_R)
            row_list.append(idx_R)
            col_list.append(idx_R)

            # Periodic wrap face: connects node (N_ax-1) ↔ node 0
            # This is the physical periodic boundary — NOT a face to node N_ax (ghost).
            if self.bc_type == 'periodic':
                idx_wL, idx_wR = self._wrap_face_indices[ax]
                rho_wL = rho_host.ravel()[idx_wL]
                rho_wR = rho_host.ravel()[idx_wR]
                coeff_w = 2.0 / (rho_wL + rho_wR) / h2

                data_list.append(coeff_w);  row_list.append(idx_wL); col_list.append(idx_wR)
                data_list.append(coeff_w);  row_list.append(idx_wR); col_list.append(idx_wL)
                data_list.append(-coeff_w); row_list.append(idx_wL); col_list.append(idx_wL)
                data_list.append(-coeff_w); row_list.append(idx_wR); col_list.append(idx_wR)

        data = np_host.concatenate(data_list)
        rows = np_host.concatenate(row_list)
        cols = np_host.concatenate(col_list)

        # Periodic BC: replace rows of ghost nodes (coordinate = N_ax along any
        # axis) with identity-minus constraints  p[ghost] = p[source].
        # These rows are first cleared, then A[ghost, ghost]=1, A[ghost, src]=-1.
        if self.bc_type == 'periodic':
            img_dofs = self._periodic_image_dofs
            src_dofs = self._periodic_image_sources
            mask = ~np_host.isin(rows, img_dofs)
            data = data[mask]
            rows = rows[mask]
            cols = cols[mask]
            # Identity-minus rows: p[ghost] - p[source] = 0
            data = np_host.concatenate([data,
                                        np_host.ones(len(img_dofs)),
                                        -np_host.ones(len(img_dofs))])
            rows = np_host.concatenate([rows, img_dofs, img_dofs])
            cols = np_host.concatenate([cols, img_dofs, src_dofs])

        # Pin one pressure degree of freedom to fix the null space.
        # p[pin] = 0  →  clear row pin and set diagonal to 1.
        pin = self._pin_dof
        mask = rows != pin
        data = data[mask]
        rows = rows[mask]
        cols = cols[mask]

        # Add A[pin, pin] = 1
        data = np_host.append(data, 1.0)
        rows = np_host.append(rows, pin)
        cols = np_host.append(cols, pin)

        return (data, rows, cols), (n, n)

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
        rhs_vec = np.asarray(self.backend.to_host(rhs_field)).ravel().copy()
        rhs_vec[self._pin_dof] = 0.0
        if self.bc_type == 'periodic' and self._periodic_image_dofs is not None:
            rhs_vec[self._periodic_image_dofs] = 0.0
        return rhs_vec

    # ── Index array pre-computation ───────────────────────────────────────

    def _build_index_arrays(self) -> None:
        """Pre-compute the flat node indices of each face type."""
        import numpy as np_host
        self._face_indices = {}

        shape = self.shape_field  # e.g. (Nx+1, Ny+1)

        for ax in range(self.ndim):
            ranges = [np_host.arange(s) for s in shape]
            N_ax = self.N[ax]

            if self.bc_type == 'periodic':
                # Internal faces: (0,1), (1,2), ..., (N_ax-2, N_ax-1)
                # The last face (N_ax-1, N_ax) is REPLACED by the wrap face below.
                ranges_L = [r.copy() for r in ranges]
                ranges_R = [r.copy() for r in ranges]
                ranges_L[ax] = np_host.arange(0, N_ax - 1)
                ranges_R[ax] = np_host.arange(1, N_ax)
            else:
                # Wall/Neumann: faces (0,1), ..., (N_ax-1, N_ax)
                ranges_L = [r.copy() for r in ranges]
                ranges_R = [r.copy() for r in ranges]
                ranges_L[ax] = np_host.arange(0, N_ax)
                ranges_R[ax] = np_host.arange(1, N_ax + 1)

            grid_L = np_host.meshgrid(*ranges_L, indexing='ij')
            grid_R = np_host.meshgrid(*ranges_R, indexing='ij')

            idx_L = np_host.ravel_multi_index(
                [g.ravel() for g in grid_L], shape
            )
            idx_R = np_host.ravel_multi_index(
                [g.ravel() for g in grid_R], shape
            )
            self._face_indices[ax] = (idx_L, idx_R)

        if self.bc_type == 'periodic':
            # Wrap faces: L = node (N_ax-1, ...), R = node (0, ...)
            # These are the physical periodic faces replacing the excluded last face.
            self._wrap_face_indices = {}
            image_to_source: dict[int, int] = {}

            for ax in range(self.ndim):
                N_ax = self.N[ax]
                ranges = [np_host.arange(s) for s in shape]

                # Wrap face nodes along this axis
                ranges_wL = [r.copy() for r in ranges]
                ranges_wR = [r.copy() for r in ranges]
                ranges_wL[ax] = np_host.array([N_ax - 1])
                ranges_wR[ax] = np_host.array([0])

                g_wL = np_host.meshgrid(*ranges_wL, indexing='ij')
                g_wR = np_host.meshgrid(*ranges_wR, indexing='ij')
                idx_wL = np_host.ravel_multi_index(
                    [g.ravel() for g in g_wL], shape
                )
                idx_wR = np_host.ravel_multi_index(
                    [g.ravel() for g in g_wR], shape
                )
                self._wrap_face_indices[ax] = (idx_wL, idx_wR)

                # Ghost (periodic image) nodes: coordinate = N_ax along this axis.
                # Their source node has coordinate 0 along the same axis.
                ranges_img = [r.copy() for r in ranges]
                ranges_src = [r.copy() for r in ranges]
                ranges_img[ax] = np_host.array([N_ax])
                ranges_src[ax] = np_host.array([0])

                g_img = np_host.meshgrid(*ranges_img, indexing='ij')
                g_src = np_host.meshgrid(*ranges_src, indexing='ij')
                idx_img = np_host.ravel_multi_index(
                    [g.ravel() for g in g_img], shape
                )
                idx_src = np_host.ravel_multi_index(
                    [g.ravel() for g in g_src], shape
                )
                # First-seen axis wins for nodes that are ghost along multiple axes.
                for im, sr in zip(idx_img.tolist(), idx_src.tolist()):
                    if im not in image_to_source:
                        image_to_source[im] = sr

            sorted_imgs = sorted(image_to_source.keys())
            self._periodic_image_dofs = np_host.array(sorted_imgs, dtype=np_host.intp)
            self._periodic_image_sources = np_host.array(
                [image_to_source[k] for k in sorted_imgs], dtype=np_host.intp
            )
        else:
            self._wrap_face_indices = {}
            self._periodic_image_dofs = None
            self._periodic_image_sources = None
