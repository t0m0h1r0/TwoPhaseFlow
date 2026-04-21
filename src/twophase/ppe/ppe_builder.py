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
        xp = self.xp
        n = self.n_dof
        ndim = self.ndim

        rho_arr = xp.asarray(rho)
        rho_flat = rho_arr.ravel()

        # Lazily upload static face-index arrays to xp (one-time per init).
        if not self._face_indices_dev:
            for ax, (idx_L, idx_R) in self._face_indices.items():
                self._face_indices_dev[ax] = (xp.asarray(idx_L),
                                              xp.asarray(idx_R))

        data_list: list = []
        row_list: list  = []
        col_list: list  = []

        # Scalar strides computed with numpy (no device needed).
        strides = [int(np.prod(self.shape_field[ax + 1:])) for ax in range(ndim)]

        for ax in range(ndim):
            N_ax = self.N[ax]
            idx_L_xp, idx_R_xp = self._face_indices_dev[ax]   # xp int arrays

            rho_L = rho_flat[idx_L_xp]
            rho_R = rho_flat[idx_R_xp]
            a_f = 2.0 / (rho_L + rho_R)   # harmonic mean face coefficient

            if not self.grid.uniform:
                # Non-uniform grid: per-face spacings precomputed once, cached.
                # Face between node k and k+1:
                #   d_face[k] = x[k+1] − x[k]  (gradient denominator)
                #   dv[i] = control volume width at node i
                cache_key = ('nonunif', ax)
                if cache_key not in self._gpu_coeff_cache:
                    coords = np.asarray(self.grid.coords[ax])
                    d_face = coords[1:] - coords[:-1]
                    dv = np.empty(len(coords))
                    dv[0]    = (coords[1] - coords[0]) / 2.0
                    dv[-1]   = (coords[-1] - coords[-2]) / 2.0
                    dv[1:-1] = (coords[2:] - coords[:-2]) / 2.0
                    idx_L_h, idx_R_h = self._face_indices[ax]   # numpy
                    stride = strides[ax]
                    ax_idx_L = (idx_L_h // stride) % self.shape_field[ax]
                    ax_idx_R = (idx_R_h // stride) % self.shape_field[ax]
                    self._gpu_coeff_cache[cache_key] = (
                        xp.asarray(d_face[ax_idx_L]),
                        xp.asarray(dv[ax_idx_L]),
                        xp.asarray(dv[ax_idx_R]),
                    )
                d_f_xp, dv_L_xp, dv_R_xp = self._gpu_coeff_cache[cache_key]
                coeff_for_L = a_f / d_f_xp / dv_L_xp
                coeff_for_R = a_f / d_f_xp / dv_R_xp
            else:
                h = float(self.grid.L[ax] / N_ax)
                h2 = h * h
                coeff = a_f / h2

                if self.bc_type == 'periodic':
                    coeff_for_L = coeff
                    coeff_for_R = coeff
                else:
                    # Node-centred boundary correction: boundary nodes have
                    # control volume h/2 → coefficient doubles. Masks cached.
                    cache_key = ('bc_mask', ax)
                    if cache_key not in self._gpu_coeff_cache:
                        idx_L_h, idx_R_h = self._face_indices[ax]
                        stride = strides[ax]
                        ax_idx_L = (idx_L_h // stride) % self.shape_field[ax]
                        ax_idx_R = (idx_R_h // stride) % self.shape_field[ax]
                        self._gpu_coeff_cache[cache_key] = (
                            xp.asarray(ax_idx_L == 0),
                            xp.asarray(ax_idx_R == N_ax),
                        )
                    mask_L, mask_R = self._gpu_coeff_cache[cache_key]
                    coeff_for_L = xp.where(mask_L, 2.0 * coeff, coeff)
                    coeff_for_R = xp.where(mask_R, 2.0 * coeff, coeff)

            # L → R, R → L, diagonal contributions
            data_list.extend([coeff_for_L, coeff_for_R, -coeff_for_L, -coeff_for_R])
            row_list.extend([idx_L_xp, idx_R_xp, idx_L_xp, idx_R_xp])
            col_list.extend([idx_R_xp, idx_L_xp, idx_L_xp, idx_R_xp])

            # Periodic wrap face: connects node (N_ax-1) ↔ node 0
            if self.bc_type == 'periodic':
                idx_wL, idx_wR = self._wrap_face_indices[ax]
                rho_wL = rho_flat[xp.asarray(idx_wL)]
                rho_wR = rho_flat[xp.asarray(idx_wR)]
                coeff_w = 2.0 / (rho_wL + rho_wR) / h2
                idx_wL_xp = xp.asarray(idx_wL)
                idx_wR_xp = xp.asarray(idx_wR)
                data_list.extend([coeff_w, coeff_w, -coeff_w, -coeff_w])
                row_list.extend([idx_wL_xp, idx_wR_xp, idx_wL_xp, idx_wR_xp])
                col_list.extend([idx_wR_xp, idx_wL_xp, idx_wL_xp, idx_wR_xp])

        data = xp.concatenate(data_list)
        rows = xp.concatenate(row_list)
        cols = xp.concatenate(col_list)

        # Periodic BC: ghost-node rows replaced by identity-minus constraints.
        # np.isin not in CuPy — pull rows to host for the mask, convert back.
        if self.bc_type == 'periodic':
            img_dofs = self._periodic_image_dofs
            src_dofs = self._periodic_image_sources
            rows_h = np.asarray(self.backend.to_host(rows))
            keep = xp.asarray(~np.isin(rows_h, img_dofs))
            data, rows, cols = data[keep], rows[keep], cols[keep]
            data = xp.concatenate([data,
                                    xp.ones(len(img_dofs)),
                                    -xp.ones(len(img_dofs))])
            rows = xp.concatenate([rows,
                                    xp.asarray(img_dofs), xp.asarray(img_dofs)])
            cols = xp.concatenate([cols,
                                    xp.asarray(img_dofs), xp.asarray(src_dofs)])

        # Pin one pressure DOF to fix the null space (p[pin] = 0).
        pin = self._pin_dof
        keep = rows != pin
        data = xp.concatenate([data[keep], xp.array([1.0])])
        rows = xp.concatenate([rows[keep], xp.array([pin], dtype=rows.dtype)])
        cols = xp.concatenate([cols[keep], xp.array([pin], dtype=cols.dtype)])

        return (data, rows, cols), (n, n)

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
