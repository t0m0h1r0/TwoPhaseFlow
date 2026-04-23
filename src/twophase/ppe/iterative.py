"""
Configurable iterative PPE solver — research toolkit.

Provides 6 combinations of discretization × iteration method for the
variable-density Pressure Poisson Equation:

    ∇·(1/ρ ∇p) = q_h

Discretization (residual evaluation accuracy):
    "ccd"  — 6th-order CCD operator (§8b); smoother uses FD → defect correction
    "3pt"  — 2nd-order 3-point central difference

Iteration method (smoother / update strategy):
    "explicit"      — explicit pseudo-time: p += Δτ R
    "gauss_seidel"  — red-black Gauss-Seidel on FD operator
    "adi"           — ADI (Thomas solver per axis, same as PPESolverSweep)

LTS (local time stepping, §8d eq:dtau_lts):
    Δτᵢⱼ = C_τ · ρᵢⱼ · h² / 2

All methods accept p_init for warm-start.  The last solution is stored
in ``last_solution`` so that one solver's output can be passed as
``p_init`` to another solver for continuation:

    p = solver_a.solve(rhs, rho, dt)
    p = solver_b.solve(rhs, rho, dt, p_init=p)   # continue from solver_a

Gauge fix: centre node (N//2, N//2) pinned to 0.
Boundary: Neumann ∂p/∂n = 0 — boundary nodes are identity in all smoothers
(same convention as PPESolverSweep).

Convergence check follows PPESolverSweep: only pin node zeroed from the
residual norm; boundary residual is included for CCD (CCD evaluates
at boundaries) and naturally zero for 3pt (interior-only stencil).
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver
    from ..core.boundary import BoundarySpec

from .interfaces import IPPESolver
from .iterative_residuals import (
    compute_density_gradient_3pt,
    compute_iterative_residual_3pt,
)
from .iterative_smoothers import (
    step_iterative_adi,
    step_iterative_explicit,
    step_iterative_gauss_seidel,
)
from .iterative_workflow import (
    IterativeSolveContext,
    compute_iterative_diagnostic_residual,
    run_iterative_solve,
)


class PPESolverIterative(IPPESolver):
    """Configurable iterative PPE solver.

    NS role
    -------
    Solves the variable-density PPE at Step 6 (§9.1 algorithm):

        ∇·[(1/ρ̃) ∇p] = (1/Δt) ∇·u*

    so that Step 7 corrector recovers divergence-free velocity:

        u^{n+1} = u* − (Δt/ρ̃) ∇p^{n+1}

    Discretisation: CCD or 3-pt FD.
    Iteration: explicit pseudo-time, Gauss-Seidel, or ADI smoother.
    Use: research toolkit.

    Parameters
    ----------
    backend        : Backend
    config         : SimulationConfig  (pseudo_tol, pseudo_maxiter, pseudo_c_tau,
                     ppe_discretization, ppe_iteration_method)
    grid           : Grid
    ccd            : CCDSolver (constructor injection; auto-built if needed)
    discretization : override for config.solver.ppe_discretization
    method         : override for config.solver.ppe_iteration_method
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
        ccd: "CCDSolver | None" = None,
        discretization: str | None = None,
        method: str | None = None,
        bc_spec: "BoundarySpec | None" = None,
    ) -> None:
        self.xp = backend.xp
        self.backend = backend
        self.ndim = grid.ndim
        self.grid = grid
        self.tol = config.solver.pseudo_tol
        self.maxiter = config.solver.pseudo_maxiter
        self.c_tau = config.solver.pseudo_c_tau

        self.discretization = discretization or getattr(
            config.solver, "ppe_discretization", "ccd"
        )
        self.method = method or getattr(
            config.solver, "ppe_iteration_method", "adi"
        )

        assert self.discretization in ("ccd", "3pt"), (
            f"ppe_discretization must be 'ccd' or '3pt': '{self.discretization}'"
        )
        assert self.method in ("explicit", "gauss_seidel", "adi"), (
            f"ppe_iteration_method must be 'explicit', 'gauss_seidel', or 'adi': "
            f"'{self.method}'"
        )

        # CCD solver (needed for CCD discretization)
        if self.discretization == "ccd":
            if ccd is not None:
                self.ccd = ccd
            else:
                from ..ccd.ccd_solver import CCDSolver as _CCD
                self.ccd = _CCD(grid, backend)
        else:
            self.ccd = ccd  # may still be passed; stored but unused

        self._h = [grid.L[ax] / grid.N[ax] for ax in range(grid.ndim)]
        self._h_min = min(self._h)

        # 境界条件仕様
        if bc_spec is not None:
            self._bc_spec = bc_spec
        else:
            from ..core.boundary import BoundarySpec as _BS
            self._bc_spec = _BS(
                bc_type=config.numerics.bc_type,
                shape=grid.shape,
                N=grid.N,
            )
        self._pin_dof = self._bc_spec.pin_dof

        # Last state for handoff: p and per-axis derivatives (dp, d2p)
        self.last_solution = None
        self._last_state: dict | None = None

    # ── IPPESolver ────────────────────────────────────────────────────────

    def solve(
        self,
        rhs,
        rho,
        dt: float,
        p_init=None,
    ):
        """Solve PPE iteratively.

        Parameters
        ----------
        rhs    : array, shape ``grid.shape`` — (1/Δt) ∇·u*_RC
        rho    : array, shape ``grid.shape`` — density field
        dt     : float (unused; kept for interface compliance)
        p_init : array, dict, or None — warm-start initial guess.
                 - None → zeros (IPC incremental δp⁰ = 0)
                 - array → use as initial p
                 - dict  → state from ``get_state()``; keys:
                   ``'p'``, ``'dp'`` (list of per-axis 1st deriv),
                   ``'d2p'`` (list of per-axis 2nd deriv).
                   Derivatives are used for the first residual evaluation
                   when the receiving solver uses CCD discretization,
                   avoiding a re-differentiation of the 3pt-quality p.

        Returns
        -------
        p : array, shape ``grid.shape``
        """
        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float)
        result, self._last_state = run_iterative_solve(
            self._solve_context(),
            rhs_np=rhs_np,
            rho_np=rho_np,
            p_init=p_init,
            residual_ccd=self._residual_ccd,
            residual_3pt=self._residual_3pt,
            ccd=self.ccd,
            thomas_sweep=self._thomas_sweep,
        )
        self.last_solution = result
        return result

    def get_state(self) -> dict:
        """Return the last solution state for handoff to another solver.

        Returns
        -------
        state : dict with keys:
            ``'p'``   — pressure field (array, shape ``grid.shape``)
            ``'dp'``  — list of 1st derivatives per axis [∂p/∂x, ∂p/∂y, ...]
            ``'d2p'`` — list of 2nd derivatives per axis [∂²p/∂x², ∂²p/∂y², ...]

        Usage::

            state = solver_3pt.get_state()
            p = solver_ccd.solve(rhs, rho, dt, p_init=state)
        """
        if self._last_state is None:
            raise RuntimeError(
                "No state available. Call solve() first."
            )
        return self._last_state

    # ── Diagnostic ───────────────────────────────────────────────────────

    def compute_residual(self, p, rhs, rho) -> float:
        """Return ‖L(p) − rhs‖₂ (diagnostic, same as _CCDPPEBase).

        Pin node is excluded from the norm (gauge constraint).
        """
        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float)
        p_np = np.asarray(self.backend.to_host(p), dtype=float)
        return compute_iterative_diagnostic_residual(
            self._solve_context(),
            p_np=p_np,
            rhs_np=rhs_np,
            rho_np=rho_np,
            residual_ccd=self._residual_ccd,
            residual_3pt=self._residual_3pt,
            ccd=self.ccd,
        )

    def _solve_context(self) -> IterativeSolveContext:
        """Build the grouped solve context shared by helpers."""
        return IterativeSolveContext(
            backend=self.backend,
            discretization=self.discretization,
            method=self.method,
            c_tau=self.c_tau,
            tol=self.tol,
            maxiter=self.maxiter,
            h=self._h,
            h_min=self._h_min,
            ndim=self.ndim,
            shape=self.grid.shape,
            pin=self._pin_dof,
        )

    # ── Density gradient (3pt) ───────────────────────────────────────────

    def _drho_3pt(self, rho_np: np.ndarray) -> list[np.ndarray]:
        """Compute ∂ρ/∂x_i via 3-point central difference (O(h²)).

        Interior: central difference.  Boundary: 2nd-order one-sided stencil.
        """
        return compute_density_gradient_3pt(
            rho_np,
            h=self._h,
            ndim=self.ndim,
        )

    # ── Residual computation ─────────────────────────────────────────────

    def _residual_ccd(
        self,
        p: np.ndarray,
        rhs_np: np.ndarray,
        rho_np: np.ndarray,
        drho: list[np.ndarray],
    ) -> tuple[np.ndarray, list[np.ndarray], list[np.ndarray]]:
        """R = rhs − L_CCD(p), CCD differentiation (O(h⁶)).

        Returns (R, dp_list, d2p_list) where dp_list[ax] and d2p_list[ax]
        are the per-axis 1st and 2nd derivatives of p.
        """
        from .ccd_ppe_utils import compute_ccd_laplacian_with_derivatives
        Lp, dp_list, d2p_list = compute_ccd_laplacian_with_derivatives(
            p, rho_np, drho, self.ccd, self.backend,
        )
        return rhs_np - Lp, dp_list, d2p_list

    def _residual_3pt(
        self,
        p: np.ndarray,
        rhs_np: np.ndarray,
        rho_np: np.ndarray,
        drho: list[np.ndarray],
    ) -> tuple[np.ndarray, list[np.ndarray], list[np.ndarray]]:
        """R = rhs − L_FD(p), 3-point central difference (O(h²)).

        Returns (R, dp_list, d2p_list).
        Interior only: boundary Lp = 0 (boundary equations are identity in
        all smoothers, so boundary residual does not affect the iteration).
        """
        return compute_iterative_residual_3pt(
            p,
            rhs_np,
            rho_np,
            drho,
            h=self._h,
            ndim=self.ndim,
            shape=self.grid.shape,
        )

    # ── Smoothers ────────────────────────────────────────────────────────

    def _step_explicit(
        self,
        p: np.ndarray,
        R: np.ndarray,
        dtau: np.ndarray,
        pin: int,
    ) -> np.ndarray:
        """Explicit pseudo-time: p += Δτ R.

        Boundary values are frozen (Neumann BC enforced implicitly).
        """
        return step_iterative_explicit(
            p,
            R,
            dtau,
            pin=pin,
            ndim=self.ndim,
        )

    def _step_gauss_seidel(
        self,
        p: np.ndarray,
        R: np.ndarray,
        rho: np.ndarray,
        drho: list[np.ndarray],
        dtau: np.ndarray,
        pin: int,
    ) -> np.ndarray:
        """Vectorized red-black Gauss-Seidel on (1/Δτ − L_FD) δp = R.

        FD stencil (product-rule form):
            (1/Δτ + 2/(ρhx²) + 2/(ρhy²)) δp[i,j]
            = R[i,j]
              + (1/(ρhx²) − dρx/(2ρ²hx)) δp[i−1,j]
              + (1/(ρhx²) + dρx/(2ρ²hx)) δp[i+1,j]
              + (1/(ρhy²) − dρy/(2ρ²hy)) δp[i,j−1]
              + (1/(ρhy²) + dρy/(2ρ²hy)) δp[i,j+1]

        Vectorised: each color pass is a single masked array operation.
        Red-black property guarantees all neighbors of a given color
        belong to the opposite color (frozen within that pass).

        Boundary nodes: identity (δp = 0 at walls).
        """
        return step_iterative_gauss_seidel(
            p,
            R,
            rho,
            drho,
            dtau,
            h=self._h,
            shape=self.grid.shape,
            pin=pin,
        )

    def _step_adi(
        self,
        p: np.ndarray,
        R: np.ndarray,
        rho: np.ndarray,
        drho: list[np.ndarray],
        dtau: np.ndarray,
        pin: int,
    ) -> np.ndarray:
        """ADI: x-sweep → y-sweep via Thomas solver.

        Same algorithm as PPESolverSweep._sweep_1d.
        """
        return step_iterative_adi(
            p,
            R,
            rho,
            drho,
            dtau,
            pin=pin,
            thomas_sweep=self._thomas_sweep,
        )

    # ── Thomas sweep (vectorized, identical to PPESolverSweep._sweep_1d) ─

    def _thomas_sweep(self, rhs_2d, rho, drho_ax, dtau, axis):
        """Thin wrapper — delegates to thomas_sweep_legacy.thomas_sweep_1d."""
        from .thomas_sweep_legacy import thomas_sweep_1d
        return thomas_sweep_1d(rhs_2d, rho, drho_ax, dtau, axis, self.grid)
