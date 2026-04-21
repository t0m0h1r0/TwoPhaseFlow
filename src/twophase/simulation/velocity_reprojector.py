"""Velocity reprojection strategy after grid remapping (4 modes).

After interface-fitted grid rebuild, linear interpolation of velocity does not
preserve ∇·u = 0, leading to O(h) spurious divergence. This module encapsulates
4 reprojection strategies:

1. **LegacyReprojector** — Uniform-grid fallback: PPE solve with uniform ρ.
2. **VariableDensityReprojector** — Variable ρ = ρ_g + (ρ_l − ρ_g) ψ.
3. **ConsistentGFMReprojector** — Alias for variable-density (GFM setup).
4. **ConsistentIIMReprojector** — Immersed interface method: jump-aware RHS
   correction with backtracking acceptance gates and statistics.

Each implements IVelocityReprojector with a unified API:
    reprojector.reproject(psi, u, v, ppe_solver, ccd, backend, rho_l, rho_g)

Statistics are collected in reprojector.stats dict (populated during reproject()).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Tuple, TYPE_CHECKING
import numpy as np
import warnings

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ppe.iim.stencil_corrector import IIMStencilCorrector
    from ..ppe.interfaces import IPPESolver


class IVelocityReprojector(ABC):
    """Abstract interface for velocity reprojection after grid rebuild."""

    @abstractmethod
    def reproject(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        ppe_solver: "IPPESolver",
        ccd: "CCDSolver",
        backend: "Backend",
        rho_l: float | None = None,
        rho_g: float | None = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Reproject velocity to satisfy ∇·u = 0 on remapped grid.

        Parameters
        ----------
        psi : ndarray  CLS field (1 = liquid, 0 = gas)
        u, v : ndarray  velocity components (remapped, may have divergence)
        ppe_solver : IPPESolver  PPE solver instance
        ccd : CCDSolver  CCD differentiation instance
        backend : Backend  array backend (CPU/GPU)
        rho_l, rho_g : float or None  densities (only used by variable-density modes)

        Returns
        -------
        u_proj, v_proj : ndarray  divergence-free velocity
        """

    @property
    @abstractmethod
    def stats(self) -> Dict[str, float]:
        """Return dict of reprojection statistics (calls, accepts, rejects, etc.)."""


class LegacyReprojector(IVelocityReprojector):
    """Uniform-grid baseline reprojector (constant ρ = 1).

    Used when reproject_mode='legacy' or as fallback for other modes.
    """

    def __init__(self) -> None:
        self._stats = {"calls": 0}

    def reproject(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        ppe_solver: "IPPESolver",
        ccd: "CCDSolver",
        backend: "Backend",
        rho_l: float | None = None,
        rho_g: float | None = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Reproject with constant ρ = 1."""
        self._stats["calls"] += 1

        def _h(arr):
            return np.asarray(backend.to_host(arr))

        xp = backend.xp
        psi = xp.asarray(psi)
        u = xp.asarray(u)
        v = xp.asarray(v)

        # Base projection: solve PPE with ρ = 1
        du_dx, _ = ccd.differentiate(u, 0)
        dv_dy, _ = ccd.differentiate(v, 1)
        div = (du_dx + dv_dy) / 1.0  # dt factor handled outside

        # Uniform density matrix
        rho = xp.ones_like(psi)
        phi = xp.asarray(ppe_solver.solve(div, rho))

        # Correct velocity
        dp_dx, _ = ccd.differentiate(phi, 0)
        dp_dy, _ = ccd.differentiate(phi, 1)
        u_proj = u - dp_dx
        v_proj = v - dp_dy

        return u_proj, v_proj

    @property
    def stats(self) -> Dict[str, float]:
        return dict(self._stats)


class VariableDensityReprojector(IVelocityReprojector):
    """Reprojector with variable density ρ = ρ_g + (ρ_l − ρ_g) ψ.

    Used when reproject_mode='variable_density_only' or 'consistent_gfm'.
    """

    def __init__(self) -> None:
        self._stats = {"calls": 0}

    def reproject(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        ppe_solver: "IPPESolver",
        ccd: "CCDSolver",
        backend: "Backend",
        rho_l: float | None = None,
        rho_g: float | None = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Reproject with variable density."""
        self._stats["calls"] += 1

        def _h(arr):
            return np.asarray(backend.to_host(arr))

        xp = backend.xp
        psi = xp.asarray(psi)
        u = xp.asarray(u)
        v = xp.asarray(v)

        # Compute density field
        if rho_l is not None and rho_g is not None:
            rho = rho_g + (rho_l - rho_g) * psi
        else:
            rho = xp.ones_like(psi)

        # Base projection
        du_dx, _ = ccd.differentiate(u, 0)
        dv_dy, _ = ccd.differentiate(v, 1)
        div = (du_dx + dv_dy) / 1.0  # dt factor handled outside

        phi = xp.asarray(ppe_solver.solve(div, rho))

        # Correct velocity
        dp_dx, _ = ccd.differentiate(phi, 0)
        dp_dy, _ = ccd.differentiate(phi, 1)
        u_proj = u - dp_dx
        v_proj = v - dp_dy

        return u_proj, v_proj

    @property
    def stats(self) -> Dict[str, float]:
        return dict(self._stats)


class ConsistentGFMReprojectorLegacy(IVelocityReprojector):
    """GFM reprojector (alias for variable-density with alternative naming).

    DO NOT DELETE — retained per rule C2. Superseded by VariableDensityReprojector.
    reproject_mode='consistent_gfm' now directly instantiates VariableDensityReprojector.
    """

    def __init__(self) -> None:
        self._delegate = VariableDensityReprojector()

    def reproject(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        ppe_solver: "IPPESolver",
        ccd: "CCDSolver",
        backend: "Backend",
        rho_l: float | None = None,
        rho_g: float | None = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Delegate to variable-density reprojector."""
        return self._delegate.reproject(psi, u, v, ppe_solver, ccd, backend, rho_l, rho_g)

    @property
    def stats(self) -> Dict[str, float]:
        return self._delegate.stats


# Backward compatibility alias
ConsistentGFMReprojector = ConsistentGFMReprojectorLegacy


class ConsistentIIMReprojector(IVelocityReprojector):
    """Immersed Interface Method (IIM) reprojector with backtracking.

    Used when reproject_mode='consistent_iim'. Attempts to solve the PPE with
    jump-aware correction ΔQ that enforces interface consistency (σ=0 mode).
    If the solution exceeds divergence acceptance gates or is non-finite,
    applies backtracking (line-search style) or falls back to variable-density.

    Maintains rich statistics: iim_attempts, iim_accepts, iim_rejects, etc.
    """

    def __init__(
        self,
        reproj_iim: "IIMStencilCorrector",
        reconstruct_base,  # HeavisideInterfaceReconstructor
    ) -> None:
        """

        Parameters
        ----------
        reproj_iim : IIMStencilCorrector
            IIM corrector instance (shared between grid-rebuild and PPE).
        reconstruct_base : HeavisideInterfaceReconstructor
            Reconstructor for phi_from_psi() conversions in IIM computation.
        """
        self._reproj_iim = reproj_iim
        self._reconstruct_base = reconstruct_base
        self._stats = {
            "calls": 0,
            "iim_attempts": 0,
            "iim_accepts": 0,
            "iim_rejects": 0,
            "iim_fails": 0,
            "iim_reject_nonfinite": 0,
            "iim_reject_divergence": 0,
            "iim_crossings_total": 0,
            "iim_crossings_accept": 0,
            "iim_crossings_reject": 0,
            "iim_div_base_sum": 0.0,
            "iim_div_iim_sum": 0.0,
            "iim_div_iim_accept_sum": 0.0,
            "iim_div_iim_reject_sum": 0.0,
            "iim_backtrack_accepts": 0,
        }
        self._warned_iim_fail = False
        self._warned_iim_reject = False
        self._delegate = VariableDensityReprojector()

    def reproject(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        ppe_solver: "IPPESolver",
        ccd: "CCDSolver",
        backend: "Backend",
        rho_l: float | None = None,
        rho_g: float | None = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Reproject using IIM with backtracking and acceptance gates."""
        self._stats["calls"] += 1

        if rho_l is None or rho_g is None:
            # Fallback to variable-density if densities not provided
            return self._delegate.reproject(psi, u, v, ppe_solver, ccd, backend, rho_l, rho_g)

        def _h(arr):
            return np.asarray(backend.to_host(arr))

        xp = backend.xp
        psi = xp.asarray(psi)
        u = xp.asarray(u)
        v = xp.asarray(v)

        # Compute density field
        rho = rho_g + (rho_l - rho_g) * psi

        # Base projection
        du_dx, _ = ccd.differentiate(u, 0)
        dv_dy, _ = ccd.differentiate(v, 1)
        div = (du_dx + dv_dy) / 1.0  # dt factor handled outside

        # Helper: apply correction and compute divergence
        def _apply_phi_and_div(phi_field):
            dp_dx, _ = ccd.differentiate(phi_field, 0)
            dp_dy, _ = ccd.differentiate(phi_field, 1)
            u_c = u - dp_dx
            v_c = v - dp_dy
            du_c_dx, _ = ccd.differentiate(u_c, 0)
            dv_c_dy, _ = ccd.differentiate(v_c, 1)
            _sum = du_c_dx + dv_c_dy
            div_check = float(xp.sqrt(xp.sum(_sum ** 2)))
            return u_c, v_c, float(div_check)

        # Base divergence (no IIM correction)
        phi_base = xp.asarray(ppe_solver.solve(div, rho))
        u_base, v_base, div_base = _apply_phi_and_div(phi_base)

        # Attempt IIM correction
        self._stats["iim_attempts"] += 1
        try:
            phi_iface = np.asarray(backend.to_host(self._reconstruct_base.phi_from_psi(psi)))
            n_cross = len(self._reproj_iim.find_interface_crossings(phi_iface))
            self._stats["iim_crossings_total"] += int(n_cross)

            # Compute IIM correction with zero curvature (reprojection mode)
            kappa0 = np.zeros_like(psi)
            A_host = ppe_solver.get_matrix(rho)
            dp0_x, _ = ccd.differentiate(phi_base, 0)
            dp0_y, _ = ccd.differentiate(phi_base, 1)

            delta_q = self._reproj_iim.compute_correction(
                A_host,
                phi_iface,
                kappa0,
                0.0,  # no Young-Laplace jump for reprojection
                rho,
                div,
                dp_dx=_h(dp0_x),
                dp_dy=_h(dp0_y),
            )

            # Solve corrected PPE (wrap delta_q to xp for GPU consistency)
            delta_q_xp = xp.asarray(delta_q)
            phi_iim = xp.asarray(ppe_solver.solve(div + delta_q_xp, rho))
            u_iim, v_iim, div_iim = _apply_phi_and_div(phi_iim)

            self._stats["iim_div_base_sum"] += float(div_base)
            self._stats["iim_div_iim_sum"] += float(div_iim)

            # Acceptance gate: finiteness + divergence reduction
            finite_ok = np.isfinite(u_iim).all() and np.isfinite(v_iim).all()
            if finite_ok and div_iim <= 1.05 * max(div_base, 1e-30):
                self._stats["iim_accepts"] += 1
                self._stats["iim_crossings_accept"] += int(n_cross)
                self._stats["iim_div_iim_accept_sum"] += float(div_iim)
                return u_iim, v_iim

            # Backtracking: try reduced correction strength
            accepted_bt = False
            best_div_bt = div_iim
            best_u_bt, best_v_bt = u_iim, v_iim
            for alpha in [0.5, 0.25, 0.1]:
                delta_q_bt = alpha * delta_q_xp
                phi_bt = xp.asarray(ppe_solver.solve(div + delta_q_bt, rho))
                u_bt, v_bt, div_bt = _apply_phi_and_div(phi_bt)

                finite_bt = np.isfinite(u_bt).all() and np.isfinite(v_bt).all()
                if finite_bt and div_bt <= 1.05 * max(div_base, 1e-30):
                    self._stats["iim_accepts"] += 1
                    self._stats["iim_crossings_accept"] += int(n_cross)
                    self._stats["iim_div_iim_accept_sum"] += float(div_bt)
                    self._stats["iim_backtrack_accepts"] += 1
                    return u_bt, v_bt

                if np.isfinite(div_bt):
                    best_div_bt = min(best_div_bt, div_bt)
                    best_u_bt, best_v_bt = u_bt, v_bt
                    accepted_bt = accepted_bt or (finite_bt and div_bt <= 1.05 * max(div_base, 1e-30))

            if accepted_bt:
                return best_u_bt, best_v_bt

            # Rejection: no candidate passed gates
            self._stats["iim_rejects"] += 1
            self._stats["iim_crossings_reject"] += int(n_cross)
            self._stats["iim_div_iim_reject_sum"] += float(div_iim)
            if not finite_ok:
                self._stats["iim_reject_nonfinite"] += 1
            else:
                self._stats["iim_reject_divergence"] += 1
            if not self._warned_iim_reject:
                warnings.warn(
                    f"consistent_iim candidate rejected; div_base={div_base:.3e}, div_iim={div_iim:.3e}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                self._warned_iim_reject = True
            return u_base, v_base

        except Exception as e:
            self._stats["iim_fails"] += 1
            if not self._warned_iim_fail:
                warnings.warn(
                    f"consistent_iim reprojection failed; fallback to base. cause={e}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                self._warned_iim_fail = True
            return u_base, v_base

    @property
    def stats(self) -> Dict[str, float]:
        return dict(self._stats)
