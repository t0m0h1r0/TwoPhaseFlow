"""
DC-Omega sweep PPE solver: Thomas ADI with under-relaxation.

Background (§8d, exp10_16–19)
------------------------------
The standard DC sweep (PPESolverSweep, omega=1) diverges when the CCD/FD
eigenvalue ratio exceeds 2 at high wavenumbers:

    spectral radius = |1 - omega * lambda_H / lambda_FD|

At Nyquist for uniform density: lambda_H/lambda_FD ≈ π²/4 ≈ 2.47.
Convergence condition: omega < 2 / max_k(lambda_H / lambda_FD).

For uniform density: omega_crit ≈ 2/2.47 ≈ 0.81.
For variable density (rho_l/rho_g >> 1): omega_crit is smaller and
depends on the interface geometry; conservative choice omega ≤ 0.5.

This class adds a single parameter omega to PPESolverSweep.  The update is:

    p^{k+1} = p^k - omega * dp     (omega=1 is the standard sweep)

Convergence target is the same CCD-accurate solution L_H p* = q (no bias).

Limitations
-----------
- The ADI splitting error (two 1D Thomas sweeps ≠ full 2D FD inverse) adds
  an extra stability constraint beyond the 1D theory.  For high density
  ratios the safe omega may be significantly below 0.81.
- omega is a constructor parameter.  If convergence fails, reduce omega
  or fall back to PPESolverCCDLU (Kronecker LU direct solve).

Recommended values
------------------
    rho_l / rho_g = 1      : omega = 0.7  (safe margin from 0.81)
    rho_l / rho_g ≤ 10     : omega = 0.5
    rho_l / rho_g ≤ 100    : omega = 0.3  (tentative; verify with MMS)
    rho_l / rho_g > 100    : use PPESolverCCDLU instead

Paper ref: §8d (defect correction + LTS), exp10_18 (omega sweep experiment)
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

from ..interfaces.ppe_solver import IPPESolver


# DO NOT DELETE — passed tests 2026-04-05
# Superseded by: PPESolverSweep(omega=...) in ppe_solver_sweep.py
# Retained for: cross-validation and regression baseline
class PPESolverDCOmega(IPPESolver):
    """Thomas ADI DC sweep with under-relaxation omega ∈ (0, 1].

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig  (pseudo_tol, pseudo_maxiter, pseudo_c_tau)
    grid    : Grid
    omega   : float — relaxation factor in (0, 1].
              omega=1 is equivalent to PPESolverSweep (may diverge).
              omega < 2 / max_k(lambda_H/lambda_FD) guarantees convergence.
              Default 0.5 is safe for rho_l/rho_g ≤ 10.
    ccd     : CCDSolver | None — injected or auto-created
    bc_spec : BoundarySpec | None
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
        omega: float = 0.5,
        ccd: "CCDSolver | None" = None,
        bc_spec: "BoundarySpec | None" = None,
    ) -> None:
        if not (0.0 < omega <= 1.0):
            raise ValueError(f"omega must be in (0, 1], got {omega}")

        self.xp = backend.xp
        self.backend = backend
        self.grid = grid
        self.omega = omega
        self.tol = config.solver.pseudo_tol
        self.maxiter = config.solver.pseudo_maxiter
        self.c_tau = config.solver.pseudo_c_tau

        if ccd is not None:
            self.ccd = ccd
        else:
            from ..ccd.ccd_solver import CCDSolver as _CCD
            self.ccd = _CCD(grid, backend)

        if bc_spec is not None:
            self._bc_spec = bc_spec
        else:
            from ..core.boundary import BoundarySpec as _BS
            self._bc_spec = _BS(
                bc_type=config.numerics.bc_type,
                shape=grid.shape,
                N=grid.N,
            )

        self._h_min = min(
            grid.L[ax] / grid.N[ax] for ax in range(grid.ndim)
        )

    # ── IPPESolver ──────────────────────────────────────────────────────────

    def solve(
        self,
        rhs,
        rho,
        dt: float,
        p_init=None,
    ):
        """DC Thomas ADI sweep with omega-relaxation.

        Parameters
        ----------
        rhs    : array, shape ``grid.shape``
        rho    : array, shape ``grid.shape`` — density field
        dt     : float (unused; kept for interface compatibility)
        p_init : optional array — warm-start initial value

        Returns
        -------
        p : array, shape ``grid.shape`` — CCD-accurate pressure (L_H p ≈ q)
        """
        shape = self.grid.shape

        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float)

        from .ccd_ppe_utils import (
            precompute_density_gradients, compute_ccd_laplacian,
            compute_lts_dtau, check_convergence,
        )
        from .thomas_sweep import thomas_sweep_1d

        dtau = compute_lts_dtau(rho_np, self.c_tau, self._h_min)

        p = (
            np.zeros(shape, dtype=float)
            if p_init is None
            else np.asarray(self.backend.to_host(p_init), dtype=float)
        )

        drho = precompute_density_gradients(rho_np, self.ccd, self.backend)
        pin_dof = self._bc_spec.pin_dof

        converged = False
        residual = float("nan")
        for _ in range(self.maxiter):
            Lp = compute_ccd_laplacian(p, rho_np, drho, self.ccd, self.backend)
            R = rhs_np - Lp

            residual, converged = check_convergence(R, pin_dof, self.tol)
            if converged:
                break

            # Thomas ADI: (1/Δτ − L_FD_x)(1/Δτ − L_FD_y) dp = R
            q  = thomas_sweep_1d(R, rho_np, drho[0], dtau, axis=0, grid=self.grid)
            q.ravel()[pin_dof] = 0.0
            dp = thomas_sweep_1d(q, rho_np, drho[1], dtau, axis=1, grid=self.grid)
            dp.ravel()[pin_dof] = 0.0

            # Under-relaxed update: p ← p − omega * dp
            # omega=1 is PPESolverSweep; omega < 2/r_max guarantees convergence.
            p = p - self.omega * dp
            p.ravel()[pin_dof] = 0.0

        if not converged:
            warnings.warn(
                f"PPESolverDCOmega(omega={self.omega}): did not converge in "
                f"{self.maxiter} iterations (final residual {residual:.3e}, "
                f"tol={self.tol:.3e}). "
                "Try reducing omega (current recommendation: omega ≤ 0.5 for "
                "rho_l/rho_g ≤ 10, or switch to PPESolverCCDLU for high density ratios).",
                RuntimeWarning,
                stacklevel=2,
            )

        if not np.isfinite(p).all():
            warnings.warn(
                "PPESolverDCOmega: non-finite values detected. "
                "Reduce omega or check the density field.",
                RuntimeWarning,
                stacklevel=2,
            )

        return self.xp.asarray(p)
