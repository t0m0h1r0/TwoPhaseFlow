"""Surface tension force strategy (CSF vs Null).

Encapsulates the choice between:
- SurfaceTensionForce: applies balanced-force κ ∇ψ / σ
- NullSurfaceTensionForce: no-op (when σ = 0)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import ClassVar, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from .gradient_operator import IGradientOperator
    from .scheme_build_ctx import SurfaceTensionBuildCtx


class INSSurfaceTensionStrategy(ABC):
    """Abstract interface for surface tension force computation."""

    _registry: ClassVar[dict[str, type["INSSurfaceTensionStrategy"]]] = {}

    def __init_subclass__(cls, **kw: object) -> None:
        super().__init_subclass__(**kw)
        for name in getattr(cls, "scheme_names", ()):
            INSSurfaceTensionStrategy._registry[name] = cls

    @classmethod
    def from_scheme(cls, name: str, ctx: "SurfaceTensionBuildCtx") -> "INSSurfaceTensionStrategy":
        """Instantiate the surface tension strategy registered under *name*."""
        klass = cls._registry.get(name)
        if klass is None:
            raise ValueError(
                f"Unknown surface_tension_scheme {name!r}. "
                f"Known: {sorted(cls._registry)}"
            )
        return klass._build(name, ctx)

    @abstractmethod
    def compute(
        self,
        kappa: "array",
        psi: "array",
        sigma: float,
        ccd: "CCDSolver",
        gradient_op: "IGradientOperator | None" = None,
        *,
        grad_op: "IGradientOperator | None" = None,
    ) -> Tuple["array", "array"]:
        """Compute surface tension force components f_x, f_y.

        Parameters
        ----------
        kappa : ndarray  interface curvature (already filtered)
        psi : ndarray  Conservative Level Set field (1 = liquid, 0 = gas)
        sigma : float  surface tension coefficient (checked for σ > 0)
        ccd : CCDSolver  differentiation operator
        gradient_op, grad_op : IGradientOperator or None
            Optional BF-consistent gradient operator for ψ. ``grad_op`` is
            accepted as the R-1.5 alias used by main.

        Returns
        -------
        f_x, f_y : ndarray  surface tension force per unit volume
        """


class SurfaceTensionForce(INSSurfaceTensionStrategy):
    """Balanced-force CSF: f = σ κ ∇ψ.

    Applied to the momentum equation; also added to PPE RHS for
    consistent balanced-force treatment.
    """

    scheme_names = ("csf",)

    @classmethod
    def _build(cls, name: str, ctx: "SurfaceTensionBuildCtx") -> "SurfaceTensionForce":
        return cls(ctx.backend)

    def __init__(self, backend: "Backend") -> None:
        """

        Parameters
        ----------
        backend : Backend
        """
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
    ) -> Tuple["array", "array"]:
        """Compute f = σ κ ∇ψ componentwise.

        R-1.5: If grad_op (FVM) provided, use for ∇ψ on non-uniform grids.
        """
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
    """No-op surface tension (Null Object pattern).

    Used when surface tension should be skipped entirely.
    """

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
    ) -> Tuple["array", "array"]:
        """Return zero force fields."""
        return self.xp.zeros_like(kappa), self.xp.zeros_like(kappa)
