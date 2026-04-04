"""
IIM-CCD PPE solver — Immersed Interface Method for sharp-interface PPE.

Solves the variable-density PPE with explicit pressure jump [p]=σκ
at the interface, enabling sharp-interface (split-PPE) treatment
while maintaining CCD O(h^6) accuracy away from the interface.

Theory (docs/memo/IIM_CCD_PPE_ShortPaper.md):
    The CCD operator assumes smooth p. At a sharp interface where
    [p]=σκ ≠ 0, near-interface stencils produce O([p]/h²) error.
    The IIM correction moves this discrepancy to the RHS:

        L^ρ p = q + Δq

    Two correction modes:
        "nearest" — zeroth-order: Δq from [p]=σκ only. Robust, O(h^2).
        "hermite" — high-order: Δq from [p],[p'],[p'']. O(h^6) if κ
                    is sufficiently accurate.

    Solver backends:
        "lu"    — CCD Kronecker + direct LU (default, guaranteed accuracy)
        "dc"    — Defect Correction (matrix-free sweeps, large-scale)

Architecture:
    PPESolverIIM(IPPESolver):
        Composes IIMStencilCorrector + either _CCDPPEBase (LU) or
        PPESolverSweep-style DC iteration. Accepts phi, kappa, sigma
        as keyword arguments to solve().

Usage:
    solver = PPESolverIIM(backend, config, grid, ccd=ccd)

    # With IIM correction:
    p = solver.solve(rhs, rho, dt, phi=phi, kappa=kappa, sigma=sigma)

    # Without correction (falls back to standard CCD-LU):
    p = solver.solve(rhs, rho, dt)
"""

from __future__ import annotations

import warnings
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver

from ..interfaces.ppe_solver import IPPESolver
from .iim import IIMStencilCorrector


class PPESolverIIM(IPPESolver):
    """CCD PPE solver with IIM interface correction.

    Supports two solve backends and two correction modes, configured
    via SimulationConfig:
        config.solver.iim_mode     : "nearest" | "hermite"
        config.solver.iim_backend  : "lu" | "dc"

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig
    grid    : Grid
    ccd     : CCDSolver (constructor injection; auto-built if None)
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
        ccd: "CCDSolver | None" = None,
    ) -> None:
        self.xp = backend.xp
        self.backend = backend
        self.grid = grid
        self.ndim = grid.ndim
        self.tol = config.solver.pseudo_tol
        self.maxiter = config.solver.pseudo_maxiter

        if ccd is not None:
            self.ccd = ccd
        else:
            from ..ccd.ccd_solver import CCDSolver as _CCD
            self.ccd = _CCD(grid, backend)

        # IIM configuration (with defaults for backward compat)
        self._iim_mode = getattr(config.solver, "iim_mode", "hermite")
        self._iim_backend = getattr(config.solver, "iim_backend", "lu")

        # IIM corrector
        self._corrector = IIMStencilCorrector(grid, mode=self._iim_mode)

        # Pre-compute 1D CCD matrices for Kronecker assembly (LU backend)
        if self._iim_backend == "lu":
            self._D1: list = []
            self._D2: list = []
            for ax in range(self.ndim):
                d1, d2 = self._build_1d_ccd_matrices(ax)
                self._D1.append(d1)
                self._D2.append(d2)

        # Sweep parameters (DC backend)
        self._c_tau = getattr(config.solver, "pseudo_c_tau", 2.0)
        self._h_min = min(grid.L[ax] / grid.N[ax] for ax in range(grid.ndim))

    # ── IPPESolver interface ─────────────────────────────────────────────

    def solve(
        self,
        rhs,
        rho,
        dt: float,
        p_init=None,
        *,
        phi=None,
        kappa=None,
        sigma: float = 0.0,
    ):
        """Solve PPE with optional IIM correction.

        Parameters
        ----------
        rhs    : array, shape grid.shape — RHS (1/Δt) ∇·u*
        rho    : array, shape grid.shape — density field
        dt     : float — time step
        p_init : optional warm-start
        phi    : optional array — level-set φ (signed distance)
        kappa  : optional array — interface curvature κ
        sigma  : float — surface tension coefficient σ

        Returns
        -------
        p : array, shape grid.shape
        """
        if self._iim_backend == "lu":
            return self._solve_lu(rhs, rho, dt, p_init,
                                  phi=phi, kappa=kappa, sigma=sigma)
        else:
            return self._solve_dc(rhs, rho, dt, p_init,
                                  phi=phi, kappa=kappa, sigma=sigma)

    # ── LU backend (Kronecker + direct solve) ────────────────────────────

    def _solve_lu(self, rhs, rho, dt, p_init, *, phi, kappa, sigma):
        """Assemble CCD Kronecker operator, apply IIM correction, direct LU."""
        import scipy.sparse as sp
        import scipy.sparse.linalg as spla

        shape = self.grid.shape
        n = int(np.prod(shape))

        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float)

        # CCD operator assembly
        xp = self.xp
        drho_np = []
        for ax in range(self.ndim):
            drho_ax, _ = self.ccd.differentiate(xp.asarray(rho_np), ax)
            drho_np.append(np.asarray(self.backend.to_host(drho_ax), dtype=float))

        L_sparse = self._build_sparse_operator(rho_np, drho_np)

        # RHS vector
        rhs_flat = rhs_np.ravel().copy()

        # IIM correction
        if phi is not None and kappa is not None and sigma > 0.0:
            phi_np = np.asarray(self.backend.to_host(phi), dtype=float)
            kap_np = np.asarray(self.backend.to_host(kappa), dtype=float)

            # For hermite mode, compute pressure gradients from previous step
            dp_dx, dp_dy = None, None
            if self._iim_mode == "hermite" and p_init is not None:
                p_prev = xp.asarray(
                    np.asarray(self.backend.to_host(p_init), dtype=float)
                )
                dp_dx_dev, _ = self.ccd.differentiate(p_prev, 0)
                dp_dy_dev, _ = self.ccd.differentiate(p_prev, 1)
                dp_dx = np.asarray(self.backend.to_host(dp_dx_dev), dtype=float)
                dp_dy = np.asarray(self.backend.to_host(dp_dy_dev), dtype=float)

            delta_q = self._corrector.compute_correction(
                L_sparse, phi_np, kap_np, sigma, rho_np, rhs_np,
                dp_dx=dp_dx, dp_dy=dp_dy,
            )
            rhs_flat += delta_q

        # Pin centre node (gauge fix)
        pin_idx = tuple(ni // 2 for ni in self.grid.N)
        pin_dof = int(np.ravel_multi_index(pin_idx, shape))
        L_lil = L_sparse.tolil()
        L_lil[pin_dof, :] = 0.0
        L_lil[pin_dof, pin_dof] = 1.0
        L_pinned = L_lil.tocsr()
        rhs_flat[pin_dof] = 0.0

        # Direct LU solve
        p_flat = spla.spsolve(L_pinned, rhs_flat)

        if not np.isfinite(p_flat).all():
            warnings.warn(
                "PPESolverIIM(lu): solver returned non-finite values.",
                RuntimeWarning, stacklevel=2,
            )

        return self.backend.to_device(p_flat.reshape(shape))

    # ── DC backend (matrix-free defect correction sweeps) ────────────────

    def _solve_dc(self, rhs, rho, dt, p_init, *, phi, kappa, sigma):
        """Defect correction with IIM: high-order CCD residual + FD sweeps.

        The IIM correction is applied within the CCD residual evaluation
        at each DC iteration (§5 of the short paper):
            d^(k) = b^{IIM} - L_H^{IIM} p^(k)
        """
        xp = self.xp
        shape = self.grid.shape

        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float)

        phi_np = kap_np = None
        if phi is not None and kappa is not None and sigma > 0.0:
            phi_np = np.asarray(self.backend.to_host(phi), dtype=float)
            kap_np = np.asarray(self.backend.to_host(kappa), dtype=float)

        # LTS virtual time step
        dtau = self._c_tau * rho_np * (self._h_min ** 2) / 2.0

        # Initial guess
        p = (
            np.zeros(shape, dtype=float)
            if p_init is None
            else np.asarray(self.backend.to_host(p_init), dtype=float)
        )

        # Density gradients (frozen during iteration)
        rho_dev = xp.asarray(rho_np)
        drho: list[np.ndarray] = []
        for ax in range(self.ndim):
            drho_ax, _ = self.ccd.differentiate(rho_dev, ax)
            drho.append(np.asarray(self.backend.to_host(drho_ax), dtype=float))

        # Gauge pin
        pin_idx = tuple(ni // 2 for ni in self.grid.N)
        pin_dof = int(np.ravel_multi_index(pin_idx, shape))

        converged = False
        for iteration in range(self.maxiter):
            # CCD residual: R = q_h - L_CCD(p)
            p_dev = xp.asarray(p)
            Lp = xp.zeros(shape, dtype=float)
            dp_arrays = []
            for ax in range(self.ndim):
                dp_ax, d2p_ax = self.ccd.differentiate(p_dev, ax)
                drho_dev = xp.asarray(drho[ax])
                Lp += d2p_ax / rho_dev - (drho_dev / rho_dev ** 2) * dp_ax
                dp_arrays.append(
                    np.asarray(self.backend.to_host(dp_ax), dtype=float)
                )

            R = rhs_np - np.asarray(self.backend.to_host(Lp))

            # Add IIM correction to residual
            if phi_np is not None and sigma > 0.0:
                # Build operator on-the-fly for correction computation
                # (only needed for sparse element access at crossings)
                L_sparse = self._build_sparse_operator_from_drho(
                    rho_np, drho,
                )
                dp_dx = dp_arrays[0] if len(dp_arrays) > 0 else None
                dp_dy = dp_arrays[1] if len(dp_arrays) > 1 else None

                delta_q = self._corrector.compute_correction(
                    L_sparse, phi_np, kap_np, sigma, rho_np, rhs_np,
                    dp_dx=dp_dx, dp_dy=dp_dy,
                )
                R += delta_q.reshape(shape)

            # Convergence check
            R_chk = R.ravel().copy()
            R_chk[pin_dof] = 0.0
            residual = float(np.sqrt(np.dot(R_chk, R_chk)))
            if residual < self.tol:
                converged = True
                break

            # x-sweep: (1/Δτ - L_FD_x) q = R
            q = self._sweep_1d(R, rho_np, drho[0], dtau, axis=0)
            q.ravel()[pin_dof] = 0.0

            # y-sweep: (1/Δτ - L_FD_y) Δp = q
            dp = self._sweep_1d(q, rho_np, drho[1], dtau, axis=1)
            dp.ravel()[pin_dof] = 0.0

            p = p + dp
            p.ravel()[pin_dof] = 0.0

        if not converged:
            warnings.warn(
                f"PPESolverIIM(dc): did not converge in {self.maxiter} "
                f"iterations (residual={residual:.3e}, tol={self.tol:.3e}).",
                RuntimeWarning, stacklevel=2,
            )

        if not np.isfinite(p).all():
            warnings.warn(
                "PPESolverIIM(dc): non-finite values detected.",
                RuntimeWarning, stacklevel=2,
            )

        return self.backend.to_device(p)

    # ── Thomas sweep (identical to PPESolverSweep._sweep_1d) ─────────────

    def _sweep_1d(
        self,
        rhs_2d: np.ndarray,
        rho: np.ndarray,
        drho: np.ndarray,
        dtau: np.ndarray,
        axis: int,
    ) -> np.ndarray:
        """(1/Δτ - L_FD_axis) q = rhs via vectorised Thomas solver."""
        N = self.grid.N[axis]
        h = self.grid.L[axis] / N
        h2 = h * h

        rhs_f = np.moveaxis(rhs_2d, axis, 0)
        rho_f = np.moveaxis(rho, axis, 0)
        drho_f = np.moveaxis(drho, axis, 0)
        dtau_f = np.moveaxis(dtau, axis, 0)

        n = N + 1

        inv_dtau = 1.0 / dtau_f
        inv_rho_h2 = 1.0 / (rho_f * h2)
        drho_h = drho_f / (rho_f ** 2 * 2.0 * h)

        a = np.empty_like(rhs_f)
        b = np.empty_like(rhs_f)
        c = np.empty_like(rhs_f)

        a[1:-1] = -inv_rho_h2[1:-1] + drho_h[1:-1]
        b[1:-1] = inv_dtau[1:-1] + 2.0 * inv_rho_h2[1:-1]
        c[1:-1] = -inv_rho_h2[1:-1] - drho_h[1:-1]

        a[0] = 0.0;  b[0] = 1.0;  c[0] = 0.0
        a[-1] = 0.0; b[-1] = 1.0; c[-1] = 0.0

        rhs_m = rhs_f.copy()
        rhs_m[0] = 0.0
        rhs_m[-1] = 0.0

        c_p = np.zeros_like(rhs_f)
        r_p = np.zeros_like(rhs_f)

        c_p[0] = c[0] / b[0]
        r_p[0] = rhs_m[0] / b[0]
        for i in range(1, n):
            denom = b[i] - a[i] * c_p[i - 1]
            c_p[i] = c[i] / denom
            r_p[i] = (rhs_m[i] - a[i] * r_p[i - 1]) / denom

        q = np.empty_like(rhs_f)
        q[-1] = r_p[-1]
        for i in range(n - 2, -1, -1):
            q[i] = r_p[i] - c_p[i] * q[i + 1]

        return np.moveaxis(q, 0, axis)

    # ── Kronecker operator assembly ──────────────────────────────────────

    def _build_1d_ccd_matrices(self, axis: int):
        """Build 1D CCD derivative matrices D1, D2 for the given axis."""
        n_pts = self.grid.N[axis] + 1
        I = np.eye(n_pts)
        if axis == 0:
            d1, d2 = self.ccd.differentiate(I, axis=0)
            return np.asarray(d1, dtype=float), np.asarray(d2, dtype=float)
        else:
            d1, d2 = self.ccd.differentiate(I, axis=1)
            return np.asarray(d1, dtype=float).T, np.asarray(d2, dtype=float).T

    def _build_sparse_operator(self, rho_np, drho_np):
        """Assemble L_CCD^ρ via Kronecker products."""
        import scipy.sparse as sp

        shape = self.grid.shape
        Nx, Ny = shape

        D2x_full = sp.kron(sp.csr_matrix(self._D2[0]), sp.eye(Ny), format='csr')
        D2y_full = sp.kron(sp.eye(Nx), sp.csr_matrix(self._D2[1]), format='csr')
        D1x_full = sp.kron(sp.csr_matrix(self._D1[0]), sp.eye(Ny), format='csr')
        D1y_full = sp.kron(sp.eye(Nx), sp.csr_matrix(self._D1[1]), format='csr')

        rho_flat = rho_np.ravel()
        inv_rho = sp.diags(1.0 / rho_flat, format='csr')
        coeff_x = sp.diags(drho_np[0].ravel() / rho_flat ** 2, format='csr')
        coeff_y = sp.diags(drho_np[1].ravel() / rho_flat ** 2, format='csr')

        L = (inv_rho @ (D2x_full + D2y_full)
             - coeff_x @ D1x_full
             - coeff_y @ D1y_full)
        return L.tocsr()

    def _build_sparse_operator_from_drho(self, rho_np, drho_list):
        """Build sparse operator for DC backend (uses pre-computed drho)."""
        # For DC mode, we need to build CCD matrices on-the-fly
        if not hasattr(self, '_D1'):
            self._D1 = []
            self._D2 = []
            for ax in range(self.ndim):
                d1, d2 = self._build_1d_ccd_matrices(ax)
                self._D1.append(d1)
                self._D2.append(d2)
        return self._build_sparse_operator(rho_np, drho_list)
