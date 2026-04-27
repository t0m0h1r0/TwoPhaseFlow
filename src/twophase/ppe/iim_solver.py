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
from .iim_solver_workflows import (
    solve_iim_dc_backend,
    solve_iim_dc_smooth,
    solve_iim_decomp_backend,
    solve_iim_lu_backend,
    solve_iim_lu_smooth,
)


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

        self._c_tau = getattr(config.solver, "pseudo_c_tau", 2.0)  # §7.9 capillary CFL safety
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
            return self._solve_decomp(rhs, rho, dt, p_init, phi=phi, kappa=kappa, sigma=sigma)
        if self._iim_backend == "lu":
            return self._solve_lu(rhs, rho, dt, p_init, phi=phi, kappa=kappa, sigma=sigma)
        return self._solve_dc(rhs, rho, dt, p_init, phi=phi, kappa=kappa, sigma=sigma)

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
        return solve_iim_decomp_backend(
            self,
            rhs,
            rho,
            dt,
            p_init,
            phi=phi,
            kappa=kappa,
            sigma=sigma,
        )

    def _lu_solve_smooth(self, rhs_np, rho_np, drho_np):
        """Kronecker LU solve for smooth fields."""
        return solve_iim_lu_smooth(self, rhs_np, rho_np, drho_np)

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
        return solve_iim_dc_smooth(self, rhs_np, rho_np, drho_np, p_init=p_init)

    # ── LU backend (legacy RHS correction) ───────────────────────────────

    def _solve_lu(self, rhs, rho, dt, p_init, *, phi, kappa, sigma):
        """CCD Kronecker + RHS correction + direct LU."""
        return solve_iim_lu_backend(
            self,
            rhs,
            rho,
            dt,
            p_init,
            phi=phi,
            kappa=kappa,
            sigma=sigma,
        )

    # ── DC backend (legacy RHS correction) ───────────────────────────────

    def _solve_dc(self, rhs, rho, dt, p_init, *, phi, kappa, sigma):
        """DC with RHS correction (legacy approach)."""
        return solve_iim_dc_backend(
            self,
            rhs,
            rho,
            dt,
            p_init,
            phi=phi,
            kappa=kappa,
            sigma=sigma,
        )
