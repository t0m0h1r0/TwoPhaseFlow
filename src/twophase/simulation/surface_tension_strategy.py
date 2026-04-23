"""Surface-tension strategy interface plus compatibility exports."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from .gradient_operator import IGradientOperator
    from .scheme_build_ctx import SurfaceTensionBuildCtx


class INSSurfaceTensionStrategy(ABC):
    """Abstract interface for surface tension force computation."""

    _registry: ClassVar[dict[str, type["INSSurfaceTensionStrategy"]]] = {}
    _aliases:  ClassVar[dict[str, str]]                               = {}

    def __init_subclass__(cls, **kw: object) -> None:
        super().__init_subclass__(**kw)
        for name in getattr(cls, "scheme_names", ()):
            INSSurfaceTensionStrategy._registry[name] = cls
        for alias, canonical in getattr(cls, "_scheme_aliases", {}).items():
            INSSurfaceTensionStrategy._aliases[alias] = canonical

    @classmethod
    def from_scheme(cls, name: str, ctx: "SurfaceTensionBuildCtx") -> "INSSurfaceTensionStrategy":
        """Instantiate the surface tension strategy registered under *name*."""
        canonical = cls._aliases.get(name, name)
        klass = cls._registry.get(canonical)
        if klass is None:
            raise ValueError(
                f"Unknown surface_tension_scheme {name!r}. "
                f"Known: {sorted(cls._registry)}"
            )
        return klass._build(canonical, ctx)

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
    ) -> tuple["array", "array"]:
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


from .surface_tension_forces import (
    NullSurfaceTensionForce,
    PressureJumpSurfaceTension,
    SurfaceTensionForce,
)

__all__ = [
    "INSSurfaceTensionStrategy",
    "SurfaceTensionForce",
    "NullSurfaceTensionForce",
    "PressureJumpSurfaceTension",
]
