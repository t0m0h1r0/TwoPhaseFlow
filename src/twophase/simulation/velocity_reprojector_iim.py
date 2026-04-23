"""IIM-based velocity reprojection implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import warnings

from ..ppe.interfaces import MatrixAssemblyUnavailable
from .velocity_reprojector import IVelocityReprojector, _device_array, _host_array
from .velocity_reprojector_basic import VariableDensityReprojector

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ppe.iim.stencil_corrector import IIMStencilCorrector
    from ..ppe.interfaces import IPPESolver
    from .scheme_build_ctx import ReprojectorBuildCtx


class ConsistentIIMReprojector(IVelocityReprojector):
    """Immersed Interface Method (IIM) reprojector with backtracking."""

    scheme_names = ("iim", "consistent_iim")

    @classmethod
    def _build(cls, name: str, ctx: "ReprojectorBuildCtx") -> "ConsistentIIMReprojector":
        return cls(ctx.iim_stencil_corrector, ctx.reconstruct_base)

    def __init__(
        self,
        reproj_iim: "IIMStencilCorrector",
        reconstruct_base,
    ) -> None:
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
    ) -> tuple[np.ndarray, np.ndarray]:
        self._stats["calls"] += 1

        if rho_l is None or rho_g is None:
            return self._delegate.reproject(psi, u, v, ppe_solver, ccd, backend, rho_l, rho_g)

        xp = backend.xp
        psi_d = _device_array(psi, backend)
        u_d = _device_array(u, backend)
        v_d = _device_array(v, backend)

        rho = rho_g + (rho_l - rho_g) * psi_d
        try:
            a_host = ppe_solver.get_matrix(rho)
        except MatrixAssemblyUnavailable:
            return self._delegate.reproject(psi, u, v, ppe_solver, ccd, backend, rho_l, rho_g)

        du_dx = ccd.first_derivative(u_d, 0)
        dv_dy = ccd.first_derivative(v_d, 1)
        div = (xp.asarray(du_dx) + xp.asarray(dv_dy)) / 1.0

        def _apply_phi_and_div(phi_field):
            dp_dx = ccd.first_derivative(phi_field, 0)
            dp_dy = ccd.first_derivative(phi_field, 1)
            u_c = u_d - xp.asarray(dp_dx)
            v_c = v_d - xp.asarray(dp_dy)
            du_c_dx = ccd.first_derivative(u_c, 0)
            dv_c_dy = ccd.first_derivative(v_c, 1)
            div_sum = xp.asarray(du_c_dx) + xp.asarray(dv_c_dy)
            div_check = float(xp.sqrt(xp.sum(div_sum**2)))
            return u_c, v_c, float(div_check)

        phi_base = ppe_solver.solve(div, rho)
        u_base, v_base, div_base = _apply_phi_and_div(phi_base)

        self._stats["iim_attempts"] += 1
        try:
            phi_iface = _host_array(self._reconstruct_base.phi_from_psi(psi_d), backend)
            n_cross = len(self._reproj_iim.find_interface_crossings(phi_iface))
            self._stats["iim_crossings_total"] += int(n_cross)

            rho_host = _host_array(rho, backend)
            div_host = _host_array(div, backend)
            kappa0 = np.zeros_like(rho_host)
            dp0_x = ccd.first_derivative(phi_base, 0)
            dp0_y = ccd.first_derivative(phi_base, 1)

            delta_q = self._reproj_iim.compute_correction(
                a_host,
                phi_iface,
                kappa0,
                0.0,
                rho_host,
                div_host,
                dp_dx=_host_array(dp0_x, backend),
                dp_dy=_host_array(dp0_y, backend),
            )

            phi_iim = ppe_solver.solve(div + xp.asarray(delta_q), rho)
            u_iim, v_iim, div_iim = _apply_phi_and_div(phi_iim)

            self._stats["iim_div_base_sum"] += float(div_base)
            self._stats["iim_div_iim_sum"] += float(div_iim)

            finite_ok = (
                np.isfinite(_host_array(u_iim, backend)).all()
                and np.isfinite(_host_array(v_iim, backend)).all()
            )
            if finite_ok and div_iim <= 1.05 * max(div_base, 1e-30):
                self._stats["iim_accepts"] += 1
                self._stats["iim_crossings_accept"] += int(n_cross)
                self._stats["iim_div_iim_accept_sum"] += float(div_iim)
                return u_iim, v_iim

            accepted_bt = False
            best_div_bt = div_iim
            best_u_bt, best_v_bt = u_iim, v_iim
            for alpha in [0.5, 0.25, 0.1]:
                delta_q_bt = alpha * delta_q
                phi_bt = ppe_solver.solve(div + xp.asarray(delta_q_bt), rho)
                u_bt, v_bt, div_bt = _apply_phi_and_div(phi_bt)

                finite_bt = (
                    np.isfinite(_host_array(u_bt, backend)).all()
                    and np.isfinite(_host_array(v_bt, backend)).all()
                )
                if finite_bt and div_bt <= 1.05 * max(div_base, 1e-30):
                    self._stats["iim_accepts"] += 1
                    self._stats["iim_crossings_accept"] += int(n_cross)
                    self._stats["iim_div_iim_accept_sum"] += float(div_bt)
                    self._stats["iim_backtrack_accepts"] += 1
                    return u_bt, v_bt

                if np.isfinite(div_bt):
                    best_div_bt = min(best_div_bt, div_bt)
                    best_u_bt, best_v_bt = u_bt, v_bt
                    accepted_bt = accepted_bt or (
                        finite_bt and div_bt <= 1.05 * max(div_base, 1e-30)
                    )

            if accepted_bt:
                return best_u_bt, best_v_bt

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

        except Exception as exc:
            self._stats["iim_fails"] += 1
            if not self._warned_iim_fail:
                warnings.warn(
                    f"consistent_iim reprojection failed; fallback to base. cause={exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                self._warned_iim_fail = True
            return u_base, v_base

    @property
    def stats(self) -> dict[str, float]:
        return dict(self._stats)
