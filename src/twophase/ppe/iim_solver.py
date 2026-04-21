"""
IIM-CCD PPE solver — Immersed Interface Method for sharp-interface PPE.

Solves the variable-density PPE with explicit pressure jump [p]=σκ
at the interface.

Three solve backends:
    "lu"      — CCD Kronecker + RHS correction + direct LU
    "dc"      — Defect correction + RHS correction (matrix-free)
    "decomp"  — Jump decomposition: p = p̃ + σκ·H_ε(φ), solve smooth p̃
                via CCD+DC on smoothed density. Recommended for sharp ρ.

Architecture:
    Inherits _CCDPPEBase for CCD matrix assembly (Kronecker products,
    1D CCD matrices, pin-node setup).  Overrides solve() with IIM-specific
    dispatch to three backends.  _solve_linear_system is not used (the
    Template Method pattern of _CCDPPEBase is bypassed).

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
    from ..core.boundary import BoundarySpec

from .ccd_ppe_base import _CCDPPEBase
from .iim import IIMStencilCorrector


class PPESolverIIM(_CCDPPEBase):
    """CCD PPE solver with IIM interface correction.

    NS role
    -------
    Solves the variable-density PPE at Step 6 (§9.1 algorithm):

        ∇·[(1/ρ̃) ∇p] = (1/Δt) ∇·u*

    so that Step 7 corrector recovers divergence-free velocity:

        u^{n+1} = u* − (Δt/ρ̃) ∇p^{n+1}

    Discretisation: CCD Kronecker O(h⁶) + IIM jump correction [p]=σκ.
    Solve: LU / defect-correction / decomposition (config-driven).

    Inherits Kronecker-product matrix assembly from _CCDPPEBase.

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig
    grid    : Grid
    ccd     : CCDSolver (constructor injection; auto-built if None)
    bc_spec : BoundarySpec (optional)
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
        ccd: "CCDSolver | None" = None,
        bc_spec: "BoundarySpec | None" = None,
    ) -> None:
        super().__init__(backend, config, grid, ccd=ccd, bc_spec=bc_spec)

        self._iim_mode = getattr(config.solver, "iim_mode", "hermite")
        self._iim_backend = getattr(config.solver, "iim_backend", "decomp")
        self._corrector = IIMStencilCorrector(grid, mode=self._iim_mode)

        self._c_tau = getattr(config.solver, "pseudo_c_tau", 2.0)
        self._h_min = min(grid.L[ax] / grid.N[ax] for ax in range(grid.ndim))

    # ── IPPESolver interface (overrides _CCDPPEBase.solve) ───────────────

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

    def _solve_linear_system(self, L_pinned, rhs_np, p0):
        """Direct LU solve (used by _assemble_pinned_system path).

        Delegates to :meth:`_CCDPPEBase._spsolve` so the GPU path uses
        :func:`cupyx.scipy.sparse.linalg.spsolve`.
        """
        return self._spsolve(L_pinned, rhs_np)

    # ── Jump Decomposition backend ───────────────────────────────────────

    def _solve_decomp(self, rhs, rho, dt, p_init, *, phi, kappa, sigma):
        """Jump decomposition: p = p̃ + σκ·H_ε(φ).

        DC反復法で p̃ を解く（LU排除）。
        """
        xp = self.xp
        shape = self.grid.shape
        h = self._h_min

        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float)

        has_iim = (phi is not None and kappa is not None and sigma > 0.0)

        if has_iim:
            phi_np = np.asarray(self.backend.to_host(phi), dtype=float)
            kap_np = np.asarray(self.backend.to_host(kappa), dtype=float)

            rho_l = float(np.max(rho_np))
            rho_g = float(np.min(rho_np))

            eps = 1.5 * h
            H_smooth = 0.5 * (1.0 + np.tanh(phi_np / (2.0 * eps)))
            rho_smooth = rho_l + (rho_g - rho_l) * H_smooth
            p_jump = sigma * kap_np * (1.0 - H_smooth)

            from .ccd_ppe_utils import precompute_density_gradients, compute_ccd_laplacian
            drho_s = precompute_density_gradients(rho_smooth, self.ccd, self.backend)
            Lp_jump = compute_ccd_laplacian(
                p_jump, rho_smooth, drho_s, self.ccd, self.backend,
            )

            rhs_tilde = rhs_np - Lp_jump
            # ✅ LU → DC反復法（LU排除）
            p_tilde = self._dc_solve_smooth(rhs_tilde, rho_smooth, drho_s, p_init=None)
            self._last_jump_field = sigma * kap_np

            # CHK-170: p = p̃ + p_jump (jump decomposition final assembly)
            p_combined = p_tilde + p_jump
            return self.backend.to_device(p_combined)
        else:
            from .ccd_ppe_utils import precompute_density_gradients
            drho = precompute_density_gradients(rho_np, self.ccd, self.backend)
            # ✅ LU → DC反復法（LU排除）
            p = self._dc_solve_smooth(rhs_np, rho_np, drho, p_init=p_init)
            return self.backend.to_device(p)

    def _lu_solve_smooth(self, rhs_np, rho_np, drho_np):
        """Kronecker LU solve for smooth fields."""
        L_sparse = self._build_sparse_operator(rho_np, drho_np)

        from ..core.boundary import pin_sparse_row
        pin_dof = self._bc_spec.pin_dof
        L_lil = L_sparse.tolil()
        rhs_flat = rhs_np.ravel().copy()
        pin_sparse_row(L_lil, rhs_flat, pin_dof)
        L_pinned = L_lil.tocsr()

        p_flat = self._spsolve(L_pinned, rhs_flat)

        if not np.isfinite(p_flat).all():
            warnings.warn(
                "PPESolverIIM(decomp): LU returned non-finite values.",
                RuntimeWarning, stacklevel=2,
            )

        return p_flat.reshape(self.grid.shape)

    def _dc_solve_smooth(self, rhs_np, rho_np, drho_np, p_init=None):
        """DC反復法で smooth field を解く（LU排除）。

        Jump decomposition内で p̃ を反復法で計算するメソッド。
        Thomas sweep × 2軸（交互方向陰解法）を使用。

        Parameters
        ----------
        rhs_np : ndarray  RHS
        rho_np : ndarray  密度場
        drho_np : tuple of ndarrays  密度勾配（軸ごと）
        p_init : ndarray, optional  初期値

        Returns
        -------
        p : ndarray  収束した圧力場
        """
        shape = self.grid.shape
        from .ccd_ppe_utils import (
            compute_ccd_laplacian_with_derivatives,
            compute_lts_dtau, check_convergence,
        )
        from .thomas_sweep_legacy import thomas_sweep_1d

        dtau = compute_lts_dtau(rho_np, self._c_tau, self._h_min)
        p = (np.zeros(shape, dtype=float) if p_init is None
             else np.asarray(p_init, dtype=float))

        pin_dof = self._bc_spec.pin_dof
        converged = False
        residual = float('inf')

        for iteration in range(self.maxiter):
            Lp, dp_arrays, _ = compute_ccd_laplacian_with_derivatives(
                p, rho_np, drho_np, self.ccd, self.backend,
            )
            R = rhs_np - Lp
            residual, converged = check_convergence(R, pin_dof, self.tol)

            if converged:
                break

            # Thomas sweep × 2軸（交互方向陰解法）
            q = thomas_sweep_1d(R, rho_np, drho_np[0], dtau, axis=0, grid=self.grid)
            q.ravel()[pin_dof] = 0.0
            dp = thomas_sweep_1d(q, rho_np, drho_np[1], dtau, axis=1, grid=self.grid)
            dp.ravel()[pin_dof] = 0.0

            p = p + dp
            p.ravel()[pin_dof] = 0.0

        if not converged:
            warnings.warn(
                f"PPESolverIIM(decomp+dc): did not converge ({residual:.3e}).",
                RuntimeWarning, stacklevel=2)

        return p

    # ── LU backend (legacy RHS correction) ───────────────────────────────

    def _solve_lu(self, rhs, rho, dt, p_init, *, phi, kappa, sigma):
        """CCD Kronecker + RHS correction + direct LU."""
        shape = self.grid.shape
        xp = self.xp

        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float)

        from .ccd_ppe_utils import precompute_density_gradients
        drho_np = precompute_density_gradients(rho_np, self.ccd, self.backend)

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

        from ..core.boundary import pin_sparse_row
        pin_dof = self._bc_spec.pin_dof
        L_lil = L_sparse.tolil()
        pin_sparse_row(L_lil, rhs_flat, pin_dof)
        L_pinned = L_lil.tocsr()

        p_flat = self._spsolve(L_pinned, rhs_flat)

        if not np.isfinite(p_flat).all():
            warnings.warn("PPESolverIIM(lu): non-finite values.",
                          RuntimeWarning, stacklevel=2)

        return self.backend.to_device(p_flat.reshape(shape))

    # ── DC backend (legacy RHS correction) ───────────────────────────────

    def _solve_dc(self, rhs, rho, dt, p_init, *, phi, kappa, sigma):
        """DC with RHS correction (legacy approach)."""
        shape = self.grid.shape

        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float)

        phi_np = kap_np = None
        if phi is not None and kappa is not None and sigma > 0.0:
            phi_np = np.asarray(self.backend.to_host(phi), dtype=float)
            kap_np = np.asarray(self.backend.to_host(kappa), dtype=float)

        from .ccd_ppe_utils import (
            precompute_density_gradients, compute_ccd_laplacian_with_derivatives,
            compute_lts_dtau, check_convergence,
        )
        from .thomas_sweep_legacy import thomas_sweep_1d

        dtau = compute_lts_dtau(rho_np, self._c_tau, self._h_min)
        p = (np.zeros(shape, dtype=float) if p_init is None
             else np.asarray(self.backend.to_host(p_init), dtype=float))

        drho = precompute_density_gradients(rho_np, self.ccd, self.backend)
        pin_dof = self._bc_spec.pin_dof

        converged = False
        residual = float('inf')
        for _ in range(self.maxiter):
            Lp, dp_arrays, _ = compute_ccd_laplacian_with_derivatives(
                p, rho_np, drho, self.ccd, self.backend,
            )
            R = rhs_np - Lp

            if phi_np is not None and sigma > 0.0:
                L_sparse = self._build_sparse_operator(rho_np, drho)
                delta_q = self._corrector.compute_correction(
                    L_sparse, phi_np, kap_np, sigma, rho_np, rhs_np,
                    dp_dx=dp_arrays[0] if dp_arrays else None,
                    dp_dy=dp_arrays[1] if len(dp_arrays) > 1 else None,
                )
                R += delta_q.reshape(shape)

            residual, converged = check_convergence(R, pin_dof, self.tol)
            if converged:
                break

            q = thomas_sweep_1d(R, rho_np, drho[0], dtau, axis=0, grid=self.grid)
            q.ravel()[pin_dof] = 0.0
            dp = thomas_sweep_1d(q, rho_np, drho[1], dtau, axis=1, grid=self.grid)
            dp.ravel()[pin_dof] = 0.0
            p = p + dp
            p.ravel()[pin_dof] = 0.0

        if not converged:
            warnings.warn(
                f"PPESolverIIM(dc): did not converge ({residual:.3e}).",
                RuntimeWarning, stacklevel=2)
        return self.backend.to_device(p)
