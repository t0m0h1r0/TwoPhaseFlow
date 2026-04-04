"""
IIM-CCD PPE solver — Immersed Interface Method for sharp-interface PPE.

Solves the variable-density PPE with explicit pressure jump [p]=σκ
at the interface.

Three solve backends:
    "lu"      — CCD Kronecker + RHS correction + direct LU
    "dc"      — Defect correction + RHS correction (matrix-free)
    "decomp"  — Jump decomposition: p = p̃ + σκ·H_ε(φ), solve smooth p̃
                via CCD+DC on smoothed density. Recommended for sharp ρ.

The "decomp" backend (jump decomposition) works by:
    1. Decompose pressure: p = p̃ + p_jump, where p_jump = σκ · H_ε(φ)
    2. p̃ is continuous (no jump) → CCD safe
    3. Substitute into PPE: L^ρ̃ p̃ = rhs - L^ρ̃ p_jump
    4. Solve for p̃ using standard CCD + defect correction
    5. Recover: p = p̃ + σκ · H(φ)  (sharp Heaviside for final result)

Usage:
    solver = PPESolverIIM(backend, config, grid, ccd=ccd)
    p = solver.solve(rhs, rho, dt, phi=phi, kappa=kappa, sigma=sigma)
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

        self._iim_mode = getattr(config.solver, "iim_mode", "hermite")
        self._iim_backend = getattr(config.solver, "iim_backend", "decomp")
        self._corrector = IIMStencilCorrector(grid, mode=self._iim_mode)

        # Pre-compute 1D CCD matrices (needed for LU and decomp backends)
        if self._iim_backend in ("lu", "decomp"):
            self._D1: list = []
            self._D2: list = []
            for ax in range(self.ndim):
                d1, d2 = self._build_1d_ccd_matrices(ax)
                self._D1.append(d1)
                self._D2.append(d2)

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
        """Solve PPE with optional IIM correction."""
        if self._iim_backend == "decomp":
            return self._solve_decomp(rhs, rho, dt, p_init,
                                      phi=phi, kappa=kappa, sigma=sigma)
        elif self._iim_backend == "lu":
            return self._solve_lu(rhs, rho, dt, p_init,
                                  phi=phi, kappa=kappa, sigma=sigma)
        else:
            return self._solve_dc(rhs, rho, dt, p_init,
                                  phi=phi, kappa=kappa, sigma=sigma)

    # ── Jump Decomposition backend ───────────────────────────────────────

    def _solve_decomp(self, rhs, rho, dt, p_init, *, phi, kappa, sigma):
        """Jump decomposition: p = p̃ + σκ·H_ε(φ).

        1. Smooth ρ with H_ε(φ) to avoid CCD Gibbs on density
        2. Compute jump field p_jump = σκ · H_ε(φ)
        3. Evaluate L^ρ̃(p_jump) via CCD (smooth field → no Gibbs)
        4. Solve L^ρ̃(p̃) = rhs - L^ρ̃(p_jump) via DC sweeps
        5. Return p = p̃ + σκ · H_sharp(φ) (sharp jump in output)

        Falls back to standard DC when phi/kappa/sigma not provided.
        """
        xp = self.xp
        shape = self.grid.shape
        h = self._h_min

        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float)

        # Determine if IIM is active
        has_iim = (phi is not None and kappa is not None and sigma > 0.0)

        if has_iim:
            phi_np = np.asarray(self.backend.to_host(phi), dtype=float)
            kap_np = np.asarray(self.backend.to_host(kappa), dtype=float)

            # Extract phase densities from the density field
            rho_l = float(np.max(rho_np))
            rho_g = float(np.min(rho_np))

            # Smoothed Heaviside for operator construction (ε = 1.5h)
            eps = 1.5 * h
            H_smooth = 0.5 * (1.0 + np.tanh(phi_np / (2.0 * eps)))

            # Smoothed density for CCD operator (no Gibbs in Dρ)
            rho_smooth = rho_l + (rho_g - rho_l) * H_smooth

            # Jump field: p_jump = σκ · (1 - H_ε(φ))
            # Adds σκ to liquid side (φ<0, H≈0), 0 to gas side (φ>0, H≈1)
            # So p_liquid = p̃ + σκ, p_gas = p̃ → [p] = p_in - p_out = σκ
            p_jump = sigma * kap_np * (1.0 - H_smooth)

            # Evaluate L^ρ̃(p_jump) via CCD
            rho_s_dev = xp.asarray(rho_smooth)
            drho_s: list[np.ndarray] = []
            for ax in range(self.ndim):
                drho_ax, _ = self.ccd.differentiate(rho_s_dev, ax)
                drho_s.append(np.asarray(self.backend.to_host(drho_ax), dtype=float))

            p_jump_dev = xp.asarray(p_jump)
            Lp_jump = xp.zeros(shape, dtype=float)
            for ax in range(self.ndim):
                dp_ax, d2p_ax = self.ccd.differentiate(p_jump_dev, ax)
                drho_dev = xp.asarray(drho_s[ax])
                Lp_jump += d2p_ax / rho_s_dev - (drho_dev / rho_s_dev**2) * dp_ax

            Lp_jump_np = np.asarray(self.backend.to_host(Lp_jump))

            # Modified RHS for smooth part: rhs_tilde = rhs - L^ρ̃(p_jump)
            rhs_tilde = rhs_np - Lp_jump_np

            # Solve for p̃ using Kronecker LU with smoothed density
            p_tilde = self._lu_solve_smooth(rhs_tilde, rho_smooth, drho_s)

            # Recover full pressure: p = p̃ + σκ · (1 - H_sharp(φ))
            # Liquid (φ<0) gets +σκ, gas (φ≥0) gets 0
            H_sharp = (phi_np >= 0.0).astype(float)
            p_full = p_tilde + sigma * kap_np * (1.0 - H_sharp)

            return self.backend.to_device(p_full)

        else:
            # No IIM — solve with Kronecker LU
            rho_dev = xp.asarray(rho_np)
            drho: list[np.ndarray] = []
            for ax in range(self.ndim):
                drho_ax, _ = self.ccd.differentiate(rho_dev, ax)
                drho.append(np.asarray(self.backend.to_host(drho_ax), dtype=float))
            p = self._lu_solve_smooth(rhs_np, rho_np, drho)
            return self.backend.to_device(p)

    def _lu_solve_smooth(self, rhs_np, rho_np, drho_np):
        """Kronecker LU solve for smooth fields.

        Assembles the CCD operator with the given density, pins the
        centre node, and solves via direct sparse LU.
        """
        import scipy.sparse.linalg as spla

        shape = self.grid.shape
        L_sparse = self._build_sparse_operator(rho_np, drho_np)

        pin_idx = tuple(ni // 2 for ni in self.grid.N)
        pin_dof = int(np.ravel_multi_index(pin_idx, shape))
        L_lil = L_sparse.tolil()
        L_lil[pin_dof, :] = 0.0
        L_lil[pin_dof, pin_dof] = 1.0
        L_pinned = L_lil.tocsr()

        rhs_flat = rhs_np.ravel().copy()
        rhs_flat[pin_dof] = 0.0

        p_flat = spla.spsolve(L_pinned, rhs_flat)

        if not np.isfinite(p_flat).all():
            warnings.warn(
                "PPESolverIIM(decomp): LU returned non-finite values.",
                RuntimeWarning, stacklevel=2,
            )

        return p_flat.reshape(shape)

    # ── LU backend (legacy RHS correction) ───────────────────────────────

    def _solve_lu(self, rhs, rho, dt, p_init, *, phi, kappa, sigma):
        """CCD Kronecker + RHS correction + direct LU."""
        import scipy.sparse.linalg as spla

        shape = self.grid.shape
        n = int(np.prod(shape))
        xp = self.xp

        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float)

        drho_np = []
        for ax in range(self.ndim):
            drho_ax, _ = self.ccd.differentiate(xp.asarray(rho_np), ax)
            drho_np.append(np.asarray(self.backend.to_host(drho_ax), dtype=float))

        L_sparse = self._build_sparse_operator(rho_np, drho_np)
        rhs_flat = rhs_np.ravel().copy()

        if phi is not None and kappa is not None and sigma > 0.0:
            phi_np = np.asarray(self.backend.to_host(phi), dtype=float)
            kap_np = np.asarray(self.backend.to_host(kappa), dtype=float)
            dp_dx, dp_dy = None, None
            if self._iim_mode == "hermite" and p_init is not None:
                p_prev = xp.asarray(np.asarray(self.backend.to_host(p_init), dtype=float))
                dp_dx_dev, _ = self.ccd.differentiate(p_prev, 0)
                dp_dy_dev, _ = self.ccd.differentiate(p_prev, 1)
                dp_dx = np.asarray(self.backend.to_host(dp_dx_dev), dtype=float)
                dp_dy = np.asarray(self.backend.to_host(dp_dy_dev), dtype=float)
            delta_q = self._corrector.compute_correction(
                L_sparse, phi_np, kap_np, sigma, rho_np, rhs_np,
                dp_dx=dp_dx, dp_dy=dp_dy,
            )
            rhs_flat += delta_q

        pin_idx = tuple(ni // 2 for ni in self.grid.N)
        pin_dof = int(np.ravel_multi_index(pin_idx, shape))
        L_lil = L_sparse.tolil()
        L_lil[pin_dof, :] = 0.0
        L_lil[pin_dof, pin_dof] = 1.0
        L_pinned = L_lil.tocsr()
        rhs_flat[pin_dof] = 0.0

        p_flat = spla.spsolve(L_pinned, rhs_flat)

        if not np.isfinite(p_flat).all():
            warnings.warn("PPESolverIIM(lu): non-finite values.",
                          RuntimeWarning, stacklevel=2)

        return self.backend.to_device(p_flat.reshape(shape))

    # ── DC backend (legacy RHS correction) ───────────────────────────────

    def _solve_dc(self, rhs, rho, dt, p_init, *, phi, kappa, sigma):
        """DC with RHS correction (legacy approach)."""
        xp = self.xp
        shape = self.grid.shape

        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float)

        phi_np = kap_np = None
        if phi is not None and kappa is not None and sigma > 0.0:
            phi_np = np.asarray(self.backend.to_host(phi), dtype=float)
            kap_np = np.asarray(self.backend.to_host(kappa), dtype=float)

        dtau = self._c_tau * rho_np * (self._h_min ** 2) / 2.0
        p = (np.zeros(shape, dtype=float) if p_init is None
             else np.asarray(self.backend.to_host(p_init), dtype=float))

        rho_dev = xp.asarray(rho_np)
        drho: list[np.ndarray] = []
        for ax in range(self.ndim):
            drho_ax, _ = self.ccd.differentiate(rho_dev, ax)
            drho.append(np.asarray(self.backend.to_host(drho_ax), dtype=float))

        pin_idx = tuple(ni // 2 for ni in self.grid.N)
        pin_dof = int(np.ravel_multi_index(pin_idx, shape))

        converged = False
        residual = float('inf')
        for _ in range(self.maxiter):
            p_dev = xp.asarray(p)
            Lp = xp.zeros(shape, dtype=float)
            dp_arrays = []
            for ax in range(self.ndim):
                dp_ax, d2p_ax = self.ccd.differentiate(p_dev, ax)
                drho_dev = xp.asarray(drho[ax])
                Lp += d2p_ax / rho_dev - (drho_dev / rho_dev**2) * dp_ax
                dp_arrays.append(np.asarray(self.backend.to_host(dp_ax), dtype=float))

            R = rhs_np - np.asarray(self.backend.to_host(Lp))

            if phi_np is not None and sigma > 0.0:
                L_sparse = self._build_sparse_operator_from_drho(rho_np, drho)
                delta_q = self._corrector.compute_correction(
                    L_sparse, phi_np, kap_np, sigma, rho_np, rhs_np,
                    dp_dx=dp_arrays[0] if dp_arrays else None,
                    dp_dy=dp_arrays[1] if len(dp_arrays) > 1 else None,
                )
                R += delta_q.reshape(shape)

            R_chk = R.ravel().copy()
            R_chk[pin_dof] = 0.0
            residual = float(np.sqrt(np.dot(R_chk, R_chk)))
            if residual < self.tol:
                converged = True
                break

            q = self._sweep_1d(R, rho_np, drho[0], dtau, axis=0)
            q.ravel()[pin_dof] = 0.0
            dp = self._sweep_1d(q, rho_np, drho[1], dtau, axis=1)
            dp.ravel()[pin_dof] = 0.0
            p = p + dp
            p.ravel()[pin_dof] = 0.0

        if not converged:
            warnings.warn(
                f"PPESolverIIM(dc): did not converge ({residual:.3e}).",
                RuntimeWarning, stacklevel=2)
        return self.backend.to_device(p)

    # ── Thomas sweep ─────────────────────────────────────────────────────

    def _sweep_1d(self, rhs_2d, rho, drho, dtau, axis):
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

    # ── Kronecker operator assembly (LU backend) ─────────────────────────

    def _build_1d_ccd_matrices(self, axis):
        n_pts = self.grid.N[axis] + 1
        I = np.eye(n_pts)
        if axis == 0:
            d1, d2 = self.ccd.differentiate(I, axis=0)
            return np.asarray(d1, dtype=float), np.asarray(d2, dtype=float)
        else:
            d1, d2 = self.ccd.differentiate(I, axis=1)
            return np.asarray(d1, dtype=float).T, np.asarray(d2, dtype=float).T

    def _build_sparse_operator(self, rho_np, drho_np):
        import scipy.sparse as sp
        Nx, Ny = self.grid.shape
        D2x_full = sp.kron(sp.csr_matrix(self._D2[0]), sp.eye(Ny), format='csr')
        D2y_full = sp.kron(sp.eye(Nx), sp.csr_matrix(self._D2[1]), format='csr')
        D1x_full = sp.kron(sp.csr_matrix(self._D1[0]), sp.eye(Ny), format='csr')
        D1y_full = sp.kron(sp.eye(Nx), sp.csr_matrix(self._D1[1]), format='csr')
        rho_flat = rho_np.ravel()
        inv_rho = sp.diags(1.0 / rho_flat, format='csr')
        coeff_x = sp.diags(drho_np[0].ravel() / rho_flat**2, format='csr')
        coeff_y = sp.diags(drho_np[1].ravel() / rho_flat**2, format='csr')
        L = inv_rho @ (D2x_full + D2y_full) - coeff_x @ D1x_full - coeff_y @ D1y_full
        return L.tocsr()

    def _build_sparse_operator_from_drho(self, rho_np, drho_list):
        if not hasattr(self, '_D1'):
            self._D1 = []
            self._D2 = []
            for ax in range(self.ndim):
                d1, d2 = self._build_1d_ccd_matrices(ax)
                self._D1.append(d1)
                self._D2.append(d2)
        return self._build_sparse_operator(rho_np, drho_list)
