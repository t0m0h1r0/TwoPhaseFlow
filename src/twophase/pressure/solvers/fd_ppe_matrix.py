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
    mat = builder.build(rho)        # scipy csr_matrix, includes pin
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
    from ...backend import Backend
    from ...core.grid import Grid
    from ...ccd.ccd_solver import CCDSolver
    from ...core.boundary import BoundarySpec


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

    def build(self, rho) -> "scipy.sparse.csr_matrix":
        """Build pinned FD matrix for the given density field.

        Parameters
        ----------
        rho : array_like, shape ``grid.shape`` (host or device)

        Returns
        -------
        scipy.sparse.csr_matrix, shape (n_dof, n_dof)
            Gauge pin row replaced by identity.
        """
        from scipy.sparse import csr_matrix
        rho_np, drho_x, drho_y = self._density_fields(rho)
        rows, cols, vals = self._assemble(rho_np, drho_x, drho_y)
        return self._apply_pin(rows, cols, vals, csr_matrix)

    def build_raw(self, rho) -> "scipy.sparse.csr_matrix":
        """Build FD matrix WITHOUT pin constraint (singular — for filter construction).

        Parameters
        ----------
        rho : array_like, shape ``grid.shape``

        Returns
        -------
        scipy.sparse.csr_matrix, shape (n_dof, n_dof) — null space = constants
        """
        from scipy.sparse import csr_matrix
        rho_np, drho_x, drho_y = self._density_fields(rho)
        rows, cols, vals = self._assemble(rho_np, drho_x, drho_y)
        return csr_matrix((vals, (rows, cols)), shape=(self._n_dof, self._n_dof))

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
        L_host = self.build(rho)
        if self.backend.is_gpu():
            L_dev = self.backend.sparse.csc_matrix(L_host.tocsc())
            return self.backend.sparse_linalg.splu(L_dev)
        return self.backend.sparse_linalg.splu(L_host.tocsc())

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
        import scipy.sparse as _sp_host

        L_raw = self.build_raw(rho)
        n = self._n_dof
        pin = self._pin_dof

        F = _sp_host.eye(n, format="lil") - alpha * L_raw.tolil()
        F[pin, :] = 0.0
        F[pin, pin] = 1.0
        F_host = F.tocsc()
        if self.backend.is_gpu():
            F_dev = self.backend.sparse.csc_matrix(F_host)
            return self.backend.sparse_linalg.splu(F_dev)
        return self.backend.sparse_linalg.splu(F_host)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _density_fields(self, rho):
        """Return (rho_np, drho_x, drho_y) as host numpy arrays."""
        xp = self.backend.xp
        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rho_dev = xp.asarray(rho_np)
        drho_x_dev, _ = self.ccd.differentiate(rho_dev, 0)
        drho_y_dev, _ = self.ccd.differentiate(rho_dev, 1)
        drho_x = np.asarray(self.backend.to_host(drho_x_dev), dtype=float)
        drho_y = np.asarray(self.backend.to_host(drho_y_dev), dtype=float)
        return rho_np, drho_x, drho_y

    def _assemble(self, rho_np, drho_x, drho_y):
        """COO assembly of the FD matrix (no pin).

        Implements ∇·(1/ρ ∇p) = ∂²p/∂x²/ρ + ∂²p/∂y²/ρ − (∂ρ·∇p)/ρ²
        with ghost-cell Neumann BC at all four walls.

        Ghost-cell rule: p[-1,j] = p[1,j] → boundary stencil = 2(p₁−p₀)/(ρh²)
        and the ∂ρ/∂n · ∂p/∂n cross term vanishes (∂p/∂n = 0 at wall).
        """
        Nx, Ny = self._N
        h = self._h
        h2 = h * h
        ny = Ny + 1   # nodes per row

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
                    coeff_bc = 2.0 * inv_rho / h2   # ghost-cell boundary stencil
                    if 0 < coord < N_ax:
                        # Interior: central FD (second + cross terms)
                        dr = drho_ax / rho_np[i, j] ** 2
                        cm = inv_rho / h2 + dr / (2 * h)   # coefficient for p[i-1,j]
                        cp = inv_rho / h2 - dr / (2 * h)   # coefficient for p[i+1,j]
                        rows += [k, k]; cols += [nb_lo, nb_hi]; vals += [cm, cp]
                        cc -= cm + cp
                    elif coord == 0:
                        # Left/bottom wall: ghost-cell Neumann
                        rows.append(k); cols.append(nb_hi); vals.append(coeff_bc)
                        cc -= coeff_bc
                    else:
                        # Right/top wall: ghost-cell Neumann
                        rows.append(k); cols.append(nb_lo); vals.append(coeff_bc)
                        cc -= coeff_bc

                rows.append(k); cols.append(k); vals.append(cc)

        return rows, cols, vals

    def _apply_pin(self, rows, cols, vals, csr_matrix):
        """Replace pin_dof row with identity and assemble CSR."""
        pin = self._pin_dof
        n = self._n_dof
        mask = [r != pin for r in rows]
        rows_p = [r for r, m in zip(rows, mask) if m] + [pin]
        cols_p = [c for c, m in zip(cols, mask) if m] + [pin]
        vals_p = [v for v, m in zip(vals, mask) if m] + [1.0]
        return csr_matrix((vals_p, (rows_p, cols_p)), shape=(n, n))
