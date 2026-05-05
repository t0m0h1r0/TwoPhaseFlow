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


def _clear_interface_for_reprojection(ppe_solver: "IPPESolver") -> None:
    clearer = getattr(ppe_solver, "clear_interface_jump_context", None)
    if callable(clearer):
        clearer()


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
        _clear_interface_for_reprojection(ppe_solver)
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

    scheme_names = ("variable_density_only",)

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

        if rho_l is None or rho_g is None:
            raise ValueError(
                "variable_density_only reprojection requires explicit rho_l and rho_g; "
                "select reproject_mode='legacy' explicitly for constant-density projection."
            )
        rho = rho_g + (rho_l - rho_g) * psi_d

        du_dx = ccd.first_derivative(u_d, 0)
        dv_dy = ccd.first_derivative(v_d, 1)
        div = (xp.asarray(du_dx) + xp.asarray(dv_dy)) / 1.0

        _clear_interface_for_reprojection(ppe_solver)
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
    """Fail-closed placeholder for the unimplemented consistent-GFM reprojector."""

    scheme_names = ("gfm", "consistent_gfm")

    def __init__(self) -> None:
        self._stats = {"calls": 0}

    @classmethod
    def _build(cls, name: str, ctx: "ReprojectorBuildCtx") -> "ConsistentGFMReprojectorLegacy":
        raise ValueError(
            f"reproject_mode={name!r} is not implemented as a GFM velocity "
            "reprojection scheme. It must not run as variable_density_only implicitly; "
            "select reproject_mode='variable_density_only' explicitly for the "
            "density-weighted projection, or choose 'consistent_iim' for the IIM path."
        )

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
        raise RuntimeError(
            "consistent_gfm velocity reprojection is not implemented; "
            "no alternate reprojection scheme was applied."
        )

    @property
    def stats(self) -> dict[str, float]:
        return dict(self._stats)


ConsistentGFMReprojector = ConsistentGFMReprojectorLegacy
