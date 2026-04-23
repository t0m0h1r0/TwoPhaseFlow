"""Concrete surface-tension strategy implementations.

Symbol mapping
--------------
κ -> ``kappa``
ψ -> ``psi``
σ -> ``sigma``
f = σ κ ∇ψ -> ``compute(...)``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .surface_tension_strategy import INSSurfaceTensionStrategy

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from .gradient_operator import IGradientOperator
    from .scheme_build_ctx import SurfaceTensionBuildCtx


class SurfaceTensionForce(INSSurfaceTensionStrategy):
    """Balanced-force CSF: f = σ κ ∇ψ."""

    scheme_names = ("csf",)

    @classmethod
    def _build(cls, name: str, ctx: "SurfaceTensionBuildCtx") -> "SurfaceTensionForce":
        return cls(ctx.backend)

    def __init__(self, backend: "Backend") -> None:
        self.xp = backend.xp

    def compute(
        self,
        kappa: "array",
        psi: "array",
        sigma: float,
        ccd: "CCDSolver",
        gradient_op: "IGradientOperator | None" = None,
        *,
        grad_op: "IGradientOperator | None" = None,
    ) -> tuple["array", "array"]:
        """Compute f = σ κ ∇ψ componentwise."""
        if sigma <= 0.0:
            return self.xp.zeros_like(kappa), self.xp.zeros_like(kappa)

        if grad_op is not None:
            gradient_op = grad_op
        if gradient_op is None:
            dpsi_dx, _ = ccd.differentiate(psi, 0)
            dpsi_dy, _ = ccd.differentiate(psi, 1)
        else:
            dpsi_dx = gradient_op.gradient(psi, 0)
            dpsi_dy = gradient_op.gradient(psi, 1)
        f_x = sigma * kappa * dpsi_dx
        f_y = sigma * kappa * dpsi_dy
        return f_x, f_y


class NullSurfaceTensionForce(INSSurfaceTensionStrategy):
    """No-op surface tension (Null Object pattern)."""

    scheme_names = ("none",)

    @classmethod
    def _build(cls, name: str, ctx: "SurfaceTensionBuildCtx") -> "NullSurfaceTensionForce":
        return cls(ctx.backend)

    def __init__(self, backend: "Backend") -> None:
        self.xp = backend.xp

    def compute(
        self,
        kappa: "array",
        psi: "array",
        sigma: float,
        ccd: "CCDSolver",
        gradient_op: "IGradientOperator | None" = None,
        *,
        grad_op: "IGradientOperator | None" = None,
    ) -> tuple["array", "array"]:
        """Return zero force fields."""
        return self.xp.zeros_like(kappa), self.xp.zeros_like(kappa)


class PressureJumpSurfaceTension(NullSurfaceTensionForce):
    """Surface tension represented as a PPE pressure jump, not CSF force."""

    scheme_names = ("pressure_jump",)
    _scheme_aliases = {
        "gfm_jump": "pressure_jump",
        "ppe_jump": "pressure_jump",
    }
