"""Basic velocity reprojector implementations.

Symbol mapping
--------------
ψ -> ``psi``
u*, v* -> ``u``, ``v``
ρ -> ``rho``
φ -> ``phi``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .velocity_reprojector import IVelocityReprojector, _device_array

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ppe.interfaces import IPPESolver
    from .scheme_build_ctx import ReprojectorBuildCtx


class LegacyReprojector(IVelocityReprojector):
    """Uniform-grid baseline reprojector (constant ρ = 1)."""

    scheme_names = ("legacy",)

    @classmethod
    def _build(cls, name: str, ctx: "ReprojectorBuildCtx") -> "LegacyReprojector":
        return cls()

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
    ) -> tuple[np.ndarray, np.ndarray]:
        self._stats["calls"] += 1

        xp = backend.xp
        psi_d = _device_array(psi, backend)
        u_d = _device_array(u, backend)
        v_d = _device_array(v, backend)

        du_dx = ccd.first_derivative(u_d, 0)
        dv_dy = ccd.first_derivative(v_d, 1)
        div = (xp.asarray(du_dx) + xp.asarray(dv_dy)) / 1.0

        rho = xp.ones_like(psi_d)
        phi = ppe_solver.solve(div, rho)

        dp_dx = ccd.first_derivative(phi, 0)
        dp_dy = ccd.first_derivative(phi, 1)
        u_proj = u_d - xp.asarray(dp_dx)
        v_proj = v_d - xp.asarray(dp_dy)
        return u_proj, v_proj

    @property
    def stats(self) -> dict[str, float]:
        return dict(self._stats)


class VariableDensityReprojector(IVelocityReprojector):
    """Reprojector with variable density ρ = ρ_g + (ρ_l − ρ_g) ψ."""

    scheme_names = ("variable_density_only", "gfm", "consistent_gfm")

    @classmethod
    def _build(cls, name: str, ctx: "ReprojectorBuildCtx") -> "VariableDensityReprojector":
        return cls()

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
    ) -> tuple[np.ndarray, np.ndarray]:
        self._stats["calls"] += 1

        xp = backend.xp
        psi_d = _device_array(psi, backend)
        u_d = _device_array(u, backend)
        v_d = _device_array(v, backend)

        if rho_l is not None and rho_g is not None:
            rho = rho_g + (rho_l - rho_g) * psi_d
        else:
            rho = xp.ones_like(psi_d)

        du_dx = ccd.first_derivative(u_d, 0)
        dv_dy = ccd.first_derivative(v_d, 1)
        div = (xp.asarray(du_dx) + xp.asarray(dv_dy)) / 1.0

        phi = ppe_solver.solve(div, rho)

        rho_inv = 1.0 / xp.where(xp.abs(rho) > 1e-30, rho, 1.0)
        dp_dx = ccd.first_derivative(phi, 0)
        dp_dy = ccd.first_derivative(phi, 1)
        u_proj = u_d - rho_inv * xp.asarray(dp_dx)
        v_proj = v_d - rho_inv * xp.asarray(dp_dy)
        return u_proj, v_proj

    @property
    def stats(self) -> dict[str, float]:
        return dict(self._stats)


class ConsistentGFMReprojectorLegacy(IVelocityReprojector):
    """Legacy alias retained per C2."""

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
    ) -> tuple[np.ndarray, np.ndarray]:
        return self._delegate.reproject(psi, u, v, ppe_solver, ccd, backend, rho_l, rho_g)

    @property
    def stats(self) -> dict[str, float]:
        return self._delegate.stats


ConsistentGFMReprojector = ConsistentGFMReprojectorLegacy
