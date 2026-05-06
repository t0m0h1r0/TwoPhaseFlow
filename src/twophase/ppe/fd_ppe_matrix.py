"""
Cell-centered FD matrix for the variable-density PPE preconditioner.

Discretises:

    L_FD p  =  ∇·(1/ρ ∇p)
             =  (∂²p/∂x² + ∂²p/∂y²) / ρ  −  (∂ρ/∂x · ∂p/∂x + ∂ρ/∂y · ∂p/∂y) / ρ²

using 2nd-order central differences on a uniform grid.

Neumann BC (∂p/∂n = 0) is implemented via ghost-cell reflection:
    p[-1] = p[1]    (left wall)
    p[N+1] = p[N-1] (right wall)

This gives the boundary stencil 2(p₁ − p₀)/(ρ h²) and zeroes the ∇ρ·∇p
cross term at walls (consistent with physical no-flux BC).

Role
----
This matrix is the **DC preconditioner**: cheap FD operator used to drive
the residual of the expensive CCD operator toward zero.  It is NOT the
high-accuracy operator — CCD (O(h⁶)) serves that role.

  L_FD ≈ L_H  (same continuous operator, lower accuracy)

Both operators share the same null space (constant pressure).  The gauge
pin (one DOF fixed to 0) is applied explicitly.

Usage
-----
    builder = FDPPEMatrix(grid, backend, ccd)
    mat = builder.build(rho)        # backend CSR matrix, includes pin
    mat_raw = builder.build_raw(rho)# without pin (singular, for filter construction)
    lu  = builder.factorize(rho)    # SuperLU object via scipy.sparse.linalg.splu
    dp  = lu.solve(rhs.ravel()).reshape(grid.shape)

Note: drho (∂ρ/∂x) is computed internally via CCD for consistency with
the CCD-based L_H used in the residual.

Paper ref: §8d (defect correction), exp10_16–19.
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver
    from ..core.boundary import BoundarySpec


class FDPPEMatrix:
    """Build the 2nd-order FD Laplacian matrix for ∇·(1/ρ ∇p) on a 2D uniform grid.

    Parameters
    ----------
    grid    : Grid (uniform 2D)
    backend : Backend
    ccd     : CCDSolver — used to compute ∂ρ/∂x, ∂ρ/∂y
    bc_spec : BoundarySpec | None — gauge pin location; default = centre node
    """

    def __init__(
        self,
        grid: "Grid",
        backend: "Backend",
        ccd: "CCDSolver",
        bc_spec: "BoundarySpec | None" = None,
    ) -> None:
        if grid.ndim != 2:
            raise NotImplementedError("FDPPEMatrix is implemented for 2D only.")
        if not grid.uniform:
            raise NotImplementedError("FDPPEMatrix requires a uniform grid.")

        self.grid = grid
        self.backend = backend
        self.xp = backend.xp
        self.ccd = ccd

        N = grid.N
        self._N = N
        self._h = float(grid.L[0] / N[0])   # uniform: same in x and y
        self._n_dof = (N[0] + 1) * (N[1] + 1)

        if bc_spec is not None:
            self._pin_dof = bc_spec.pin_dof
        else:
            # Default: centre node (invariant under all square symmetries)
            cx, cy = N[0] // 2, N[1] // 2
            self._pin_dof = cx * (N[1] + 1) + cy

    # ── Public API ────────────────────────────────────────────────────────────

    def build(self, rho):
        """Build pinned FD matrix for the given density field.

        Parameters
        ----------
        rho : array_like, shape ``grid.shape`` (host or device)

        Returns
        -------
        backend CSR matrix, shape (n_dof, n_dof)
            Gauge pin row replaced by identity.
        """
        rows, cols, vals = self._assemble(rho)
        rows, cols, vals = self._apply_pin_to_coo(rows, cols, vals)
        return self._sparse_matrix(rows, cols, vals, sparse_format="csr")

    def build_raw(self, rho):
        """Build FD matrix WITHOUT pin constraint (singular — for filter construction).

        Parameters
        ----------
        rho : array_like, shape ``grid.shape``

        Returns
        -------
        backend CSR matrix, shape (n_dof, n_dof) — null space = constants
        """
        rows, cols, vals = self._assemble(rho)
        return self._sparse_matrix(rows, cols, vals, sparse_format="csr")

    def factorize(self, rho):
        """Build and SuperLU-factorize the pinned matrix.

        Parameters
        ----------
        rho : array_like, shape ``grid.shape``

        Returns
        -------
        SuperLU object — call ``.solve(rhs_flat)`` to apply L_FD^{-1}.
        Runs on the active device: CPU → scipy SuperLU, GPU → cuDSS via
        ``cupyx.scipy.sparse.linalg.splu``.
        """
        return self.backend.sparse_linalg.splu(self.build(rho).tocsc())

    def build_helmholtz_filter(self, rho, alpha: float):
        """Factorize the FD Helmholtz filter (I − α L_FD) with pin row = identity.

        Applying this filter after each DC step stabilises divergence:
            p_filtered = (I − α L_FD)^{-1} p_raw

        Transfer function: G(k) = 1 / (1 + α |λ_FD(k)|) ∈ (0, 1] — low-pass.

        Stability condition for combined DC+filter:
            α > (λ_H/λ_FD − 2) / |λ_FD|  ≈  0.12 h²  (uniform density, Nyquist)

        Warning: introduces a fixed-point bias O(α/h²) that degrades CCD
        O(h⁶) accuracy to O(h²).  Use for low density ratios only.

        Parameters
        ----------
        rho   : array_like, shape ``grid.shape``
        alpha : float — filter strength (recommend 0.25 * h² to 1.0 * h²)

        Returns
        -------
        SuperLU object — call ``.solve(p_flat)`` to apply the filter. The
        factor lives on the active device.
        """
        n = self._n_dof
        pin = self._pin_dof
        xp = self.xp
        rows, cols, vals = self._assemble(rho)
        diag = xp.arange(n, dtype=rows.dtype)
        rows = xp.concatenate([rows, diag])
        cols = xp.concatenate([cols, diag])
        vals = xp.concatenate([
            -float(alpha) * vals,
            xp.ones(n, dtype=vals.dtype),
        ])
        mask = rows != pin
        rows = xp.concatenate([rows[mask], xp.asarray([pin], dtype=rows.dtype)])
        cols = xp.concatenate([cols[mask], xp.asarray([pin], dtype=cols.dtype)])
        vals = xp.concatenate([vals[mask], xp.asarray([1.0], dtype=vals.dtype)])
        return self.backend.sparse_linalg.splu(
            self._sparse_matrix(rows, cols, vals, sparse_format="csc")
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _density_fields(self, rho):
        """Return ``(rho, drho_x, drho_y)`` on the active backend."""
        xp = self.xp
        rho_dev = xp.asarray(rho, dtype=xp.float64)
        drho_x, _ = self.ccd.differentiate(rho_dev, 0)
        drho_y, _ = self.ccd.differentiate(rho_dev, 1)
        return rho_dev, xp.asarray(drho_x), xp.asarray(drho_y)

    def _assemble(self, rho):
        """Backend-native COO assembly of the FD matrix (no pin).

        Implements ∇·(1/ρ ∇p) = ∂²p/∂x²/ρ + ∂²p/∂y²/ρ − (∂ρ·∇p)/ρ²
        with ghost-cell Neumann BC at all four walls.

        Ghost-cell rule: p[-1,j] = p[1,j] → boundary stencil = 2(p₁−p₀)/(ρh²)
        and the ∂ρ/∂n · ∂p/∂n cross term vanishes (∂p/∂n = 0 at wall).
        """
        Nx, Ny = self._N
        xp = self.xp
        h = self._h
        h2 = h * h
        ny = Ny + 1   # nodes per row
        rho_dev, drho_x, drho_y = self._density_fields(rho)
        inv_rho = 1.0 / rho_dev
        inv_rho_h2 = inv_rho / h2
        node = xp.arange(self._n_dof, dtype=xp.int32).reshape(Nx + 1, Ny + 1)
        diag = xp.zeros((Nx + 1, Ny + 1), dtype=xp.float64)

        rows_parts = []
        cols_parts = []
        vals_parts = []

        def add(row_block, col_block, value_block):
            rows_parts.append(row_block.ravel())
            cols_parts.append(col_block.ravel())
            vals_parts.append(value_block.ravel())

        # x-axis interior: central FD plus variable-density cross term.
        x_cross = drho_x / (rho_dev * rho_dev * (2.0 * h))
        cm_x = inv_rho_h2 + x_cross
        cp_x = inv_rho_h2 - x_cross
        add(node[1:Nx, :], node[0:Nx - 1, :], cm_x[1:Nx, :])
        add(node[1:Nx, :], node[2:Nx + 1, :], cp_x[1:Nx, :])
        diag[1:Nx, :] -= cm_x[1:Nx, :] + cp_x[1:Nx, :]

        coeff_x = 2.0 * inv_rho_h2
        add(node[0:1, :], node[1:2, :], coeff_x[0:1, :])
        add(node[Nx:Nx + 1, :], node[Nx - 1:Nx, :], coeff_x[Nx:Nx + 1, :])
        diag[0:1, :] -= coeff_x[0:1, :]
        diag[Nx:Nx + 1, :] -= coeff_x[Nx:Nx + 1, :]

        # y-axis interior: central FD plus variable-density cross term.
        y_cross = drho_y / (rho_dev * rho_dev * (2.0 * h))
        cm_y = inv_rho_h2 + y_cross
        cp_y = inv_rho_h2 - y_cross
        add(node[:, 1:Ny], node[:, 0:Ny - 1], cm_y[:, 1:Ny])
        add(node[:, 1:Ny], node[:, 2:Ny + 1], cp_y[:, 1:Ny])
        diag[:, 1:Ny] -= cm_y[:, 1:Ny] + cp_y[:, 1:Ny]

        coeff_y = 2.0 * inv_rho_h2
        add(node[:, 0:1], node[:, 1:2], coeff_y[:, 0:1])
        add(node[:, Ny:Ny + 1], node[:, Ny - 1:Ny], coeff_y[:, Ny:Ny + 1])
        diag[:, 0:1] -= coeff_y[:, 0:1]
        diag[:, Ny:Ny + 1] -= coeff_y[:, Ny:Ny + 1]

        add(node, node, diag)
        return (
            xp.concatenate(rows_parts),
            xp.concatenate(cols_parts),
            xp.concatenate(vals_parts),
        )

    def _apply_pin_to_coo(self, rows, cols, vals):
        """Replace pin_dof row with identity in backend-native COO arrays."""
        pin = self._pin_dof
        xp = self.xp
        mask = rows != pin
        return (
            xp.concatenate([rows[mask], xp.asarray([pin], dtype=rows.dtype)]),
            xp.concatenate([cols[mask], xp.asarray([pin], dtype=cols.dtype)]),
            xp.concatenate([vals[mask], xp.asarray([1.0], dtype=vals.dtype)]),
        )

    def _sparse_matrix(self, rows, cols, vals, *, sparse_format: str):
        sparse = self.backend.sparse
        matrix_cls = sparse.csr_matrix if sparse_format == "csr" else sparse.csc_matrix
        return matrix_cls((vals, (rows, cols)), shape=(self._n_dof, self._n_dof))

    # ── C2: pre-GPU vectorization reference ─────────────────────────────
    def _assemble_host_legacy(self, rho_np, drho_x, drho_y):
        """DO NOT DELETE — pre-GPU host-loop COO baseline for regression audits."""
        Nx, Ny = self._N
        h = self._h
        h2 = h * h
        ny = Ny + 1

        def idx(i, j):
            return i * ny + j

        rows, cols, vals = [], [], []
        for i in range(Nx + 1):
            for j in range(Ny + 1):
                k = idx(i, j)
                inv_rho = 1.0 / rho_np[i, j]
                cc = 0.0
                for ax_idx, (coord, drho_ax, nb_lo, nb_hi) in enumerate([
                    (i, drho_x[i, j], idx(i - 1, j), idx(i + 1, j)),
                    (j, drho_y[i, j], idx(i, j - 1), idx(i, j + 1)),
                ]):
                    N_ax = Nx if ax_idx == 0 else Ny
                    coeff_bc = 2.0 * inv_rho / h2
                    if 0 < coord < N_ax:
                        dr = drho_ax / rho_np[i, j] ** 2
                        cm = inv_rho / h2 + dr / (2 * h)
                        cp = inv_rho / h2 - dr / (2 * h)
                        rows += [k, k]; cols += [nb_lo, nb_hi]; vals += [cm, cp]
                        cc -= cm + cp
                    elif coord == 0:
                        rows.append(k); cols.append(nb_hi); vals.append(coeff_bc)
                        cc -= coeff_bc
                    else:
                        rows.append(k); cols.append(nb_lo); vals.append(coeff_bc)
                        cc -= coeff_bc
                rows.append(k); cols.append(k); vals.append(cc)
        return rows, cols, vals
