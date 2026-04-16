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
import warnings
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver
    from ..core.boundary import BoundarySpec

from .interfaces import IPPESolver


class PPESolverIterative(IPPESolver):
    """Configurable iterative PPE solver.

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
        xp = self.xp
        shape = self.grid.shape
        pin = self._pin_dof

        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float)

        from .ccd_ppe_utils import (
            precompute_density_gradients, compute_lts_dtau, check_convergence,
        )

        # LTS: stability limit for explicit pseudo-time
        if self.method == "explicit":
            c_limit = 0.19 if self.discretization == "ccd" else 0.45
            c_eff = min(self.c_tau, c_limit)
        else:
            c_eff = self.c_tau
        dtau = compute_lts_dtau(rho_np, c_eff, self._h_min)

        # Unpack initial state (dict from get_state() or plain array)
        if isinstance(p_init, dict):
            p = np.asarray(self.backend.to_host(p_init["p"]), dtype=float)
        elif p_init is not None:
            p = np.asarray(self.backend.to_host(p_init), dtype=float)
        else:
            p = np.zeros(shape, dtype=float)

        # Density gradient (frozen during iteration)
        if self.discretization == "ccd":
            drho = precompute_density_gradients(rho_np, self.ccd, self.backend)
        else:
            drho = self._drho_3pt(rho_np)

        # Per-axis derivatives of p (updated each iteration for state output)
        last_dp: list[np.ndarray] = [np.zeros(shape) for _ in range(self.ndim)]
        last_d2p: list[np.ndarray] = [np.zeros(shape) for _ in range(self.ndim)]

        converged = False
        residual = np.inf
        for _ in range(self.maxiter):
            # ── Residual R = rhs − L(p) ─────────────────────────────
            # Always use this solver's own discretization for residual,
            # even when p_init came from a different discretization.
            if self.discretization == "ccd":
                R, dp_list, d2p_list = self._residual_ccd(
                    p, rhs_np, rho_np, drho,
                )
            else:
                R, dp_list, d2p_list = self._residual_3pt(
                    p, rhs_np, rho_np, drho,
                )
            last_dp = dp_list
            last_d2p = d2p_list

            residual, converged = check_convergence(R, pin, self.tol)
            if converged:
                break

            # ── Update step ──────────────────────────────────────────
            # Sign convention: L has negative eigenvalues (Laplacian), so the
            # correct pseudo-time update is p -= Δτ R (damped iteration on the
            # positive-definite system −L p = −rhs).  Negate R for smoothers.
            neg_R = -R
            if self.method == "explicit":
                p = self._step_explicit(p, neg_R, dtau, pin)
            elif self.method == "gauss_seidel":
                p = self._step_gauss_seidel(p, neg_R, rho_np, drho, dtau, pin)
            elif self.method == "adi":
                p = self._step_adi(p, neg_R, rho_np, drho, dtau, pin)

        if not converged:
            warnings.warn(
                f"PPESolverIterative({self.discretization},{self.method}): "
                f"not converged after {self.maxiter} iterations "
                f"(residual={residual:.3e}, tol={self.tol:.3e}).",
                RuntimeWarning,
                stacklevel=2,
            )

        if not np.isfinite(p).all():
            warnings.warn(
                "PPESolverIterative: non-finite values detected. "
                "Check the density field or reduce pseudo_c_tau.",
                RuntimeWarning,
                stacklevel=2,
            )

        result = self.backend.to_device(p)
        self.last_solution = result
        self._last_state = {
            "p": result,
            "dp": [self.backend.to_device(d) for d in last_dp],
            "d2p": [self.backend.to_device(d) for d in last_d2p],
        }
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

        from .ccd_ppe_utils import precompute_density_gradients, check_convergence
        if self.discretization == "ccd":
            drho = precompute_density_gradients(rho_np, self.ccd, self.backend)
            R, _, _ = self._residual_ccd(p_np, rhs_np, rho_np, drho)
        else:
            drho = self._drho_3pt(rho_np)
            R, _, _ = self._residual_3pt(p_np, rhs_np, rho_np, drho)

        residual, _ = check_convergence(R, self._pin_dof, 0.0)
        return residual

    # ── Density gradient (3pt) ───────────────────────────────────────────

    def _drho_3pt(self, rho_np: np.ndarray) -> list[np.ndarray]:
        """Compute ∂ρ/∂x_i via 3-point central difference (O(h²)).

        Interior: central difference.  Boundary: 2nd-order one-sided stencil.
        """
        drho: list[np.ndarray] = []
        for ax in range(self.ndim):
            h = self._h[ax]
            dr = np.zeros_like(rho_np)
            # Interior central difference
            slc_p = [slice(None)] * self.ndim
            slc_m = [slice(None)] * self.ndim
            slc_c = [slice(None)] * self.ndim
            slc_p[ax] = slice(2, None)
            slc_m[ax] = slice(None, -2)
            slc_c[ax] = slice(1, -1)
            dr[tuple(slc_c)] = (
                rho_np[tuple(slc_p)] - rho_np[tuple(slc_m)]
            ) / (2.0 * h)
            # Left boundary: (-3f0 + 4f1 - f2) / (2h)
            s0 = [slice(None)] * self.ndim; s0[ax] = 0
            s1 = [slice(None)] * self.ndim; s1[ax] = 1
            s2 = [slice(None)] * self.ndim; s2[ax] = 2
            dr[tuple(s0)] = (
                -3.0 * rho_np[tuple(s0)]
                + 4.0 * rho_np[tuple(s1)]
                - rho_np[tuple(s2)]
            ) / (2.0 * h)
            # Right boundary: (3fN - 4fN-1 + fN-2) / (2h)
            sN = [slice(None)] * self.ndim; sN[ax] = -1
            sNm1 = [slice(None)] * self.ndim; sNm1[ax] = -2
            sNm2 = [slice(None)] * self.ndim; sNm2[ax] = -3
            dr[tuple(sN)] = (
                3.0 * rho_np[tuple(sN)]
                - 4.0 * rho_np[tuple(sNm1)]
                + rho_np[tuple(sNm2)]
            ) / (2.0 * h)
            drho.append(dr)
        return drho

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
        shape = self.grid.shape
        Lp = np.zeros(shape, dtype=float)
        dp_list: list[np.ndarray] = []
        d2p_list: list[np.ndarray] = []
        for ax in range(self.ndim):
            h = self._h[ax]
            h2 = h * h
            slc_p = [slice(None)] * self.ndim
            slc_m = [slice(None)] * self.ndim
            slc_c = [slice(None)] * self.ndim
            slc_p[ax] = slice(2, None)
            slc_m[ax] = slice(None, -2)
            slc_c[ax] = slice(1, -1)
            # d²p/dx²
            d2p = np.zeros(shape, dtype=float)
            d2p[tuple(slc_c)] = (
                p[tuple(slc_p)] - 2.0 * p[tuple(slc_c)] + p[tuple(slc_m)]
            ) / h2
            # dp/dx
            dp_ax = np.zeros(shape, dtype=float)
            dp_ax[tuple(slc_c)] = (
                p[tuple(slc_p)] - p[tuple(slc_m)]
            ) / (2.0 * h)
            Lp += d2p / rho_np - (drho[ax] / rho_np ** 2) * dp_ax
            dp_list.append(dp_ax)
            d2p_list.append(d2p)
        return rhs_np - Lp, dp_list, d2p_list

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
        # Only update interior; boundary stays at initial value
        p = p.copy()
        for ax in range(self.ndim):
            s0 = [slice(None)] * self.ndim; s0[ax] = 0
            sN = [slice(None)] * self.ndim; sN[ax] = -1
            R[tuple(s0)] = 0.0
            R[tuple(sN)] = 0.0
        p += dtau * R
        p.ravel()[pin] = 0.0
        return p

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
        shape = self.grid.shape
        Nx, Ny = shape
        hx, hy = self._h[0], self._h[1]

        inv_rho = 1.0 / rho
        ax_c = inv_rho / (hx * hx)
        ay_c = inv_rho / (hy * hy)
        bx = drho[0] / (rho ** 2 * 2.0 * hx)
        by = drho[1] / (rho ** 2 * 2.0 * hy)

        diag = 1.0 / dtau + 2.0 * ax_c + 2.0 * ay_c
        c_xm = ax_c - bx
        c_xp = ax_c + bx
        c_ym = ay_c - by
        c_yp = ay_c + by

        dp = np.zeros(shape, dtype=float)
        pin_ij = np.unravel_index(pin, shape)

        # Pre-compute red/black masks for interior nodes
        ii = np.arange(1, Nx - 1)[:, None]
        jj = np.arange(1, Ny - 1)[None, :]

        # Red-black sweep (color 0 = red, 1 = black)
        for color in range(2):
            mask = ((ii + jj) % 2 == color)
            # Exclude pin DOF
            if 1 <= pin_ij[0] < Nx - 1 and 1 <= pin_ij[1] < Ny - 1:
                mask[pin_ij[0] - 1, pin_ij[1] - 1] = False

            # Interior slice views (all arrays are (Nx, Ny))
            rhs_update = (
                R[1:-1, 1:-1]
                + c_xm[1:-1, 1:-1] * dp[:-2, 1:-1]
                + c_xp[1:-1, 1:-1] * dp[2:, 1:-1]
                + c_ym[1:-1, 1:-1] * dp[1:-1, :-2]
                + c_yp[1:-1, 1:-1] * dp[1:-1, 2:]
            )
            update_vals = rhs_update / diag[1:-1, 1:-1]
            dp[1:-1, 1:-1] = np.where(mask, update_vals, dp[1:-1, 1:-1])

        p = p + dp
        p.ravel()[pin] = 0.0
        return p

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
        q = self._thomas_sweep(R, rho, drho[0], dtau, axis=0)
        q.ravel()[pin] = 0.0
        dp = self._thomas_sweep(q, rho, drho[1], dtau, axis=1)
        dp.ravel()[pin] = 0.0
        p = p + dp
        p.ravel()[pin] = 0.0
        return p

    # ── Thomas sweep (vectorized, identical to PPESolverSweep._sweep_1d) ─

    def _thomas_sweep(self, rhs_2d, rho, drho_ax, dtau, axis):
        """Thin wrapper — delegates to thomas_sweep_legacy.thomas_sweep_1d."""
        from .thomas_sweep_legacy import thomas_sweep_1d
        return thomas_sweep_1d(rhs_2d, rho, drho_ax, dtau, axis, self.grid)
