"""Viscous predictor interface plus compatibility exports."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from .scheme_build_ctx import ViscousBuildCtx


class IViscousPredictor(ABC):
    """Abstract interface for viscous predictor (advance velocity with viscous term)."""

    _registry: ClassVar[dict[str, type["IViscousPredictor"]]] = {}
    _aliases:  ClassVar[dict[str, str]]                       = {}

    def __init_subclass__(cls, **kw: object) -> None:
        super().__init_subclass__(**kw)
        for name in getattr(cls, "scheme_names", ()):
            IViscousPredictor._registry[name] = cls
        for alias, canonical in getattr(cls, "_scheme_aliases", {}).items():
            IViscousPredictor._aliases[alias] = canonical

    @classmethod
    def from_scheme(cls, name: str, ctx: "ViscousBuildCtx") -> "IViscousPredictor":
        """Instantiate the viscous predictor registered under *name*."""
        canonical = cls._aliases.get(name, name)
        klass = cls._registry.get(canonical)
        if klass is None:
            raise ValueError(
                f"Unknown viscous time scheme {name!r}. "
                f"Known: {sorted(cls._registry)}"
            )
        return klass._build(canonical, ctx)

    @abstractmethod
    def predict(
        self,
        u: "array",
        v: "array",
        conv_u: "array",
        conv_v: "array",
        mu: "array",
        rho: "array",
        dt: float,
        ccd: "CCDSolver",
        buoy_v: "array" | None = None,
        psi: "array" | None = None,
    ) -> tuple["array", "array"]:
        """Advance velocity with viscous + convection + optional buoyancy.

        Parameters
        ----------
        u, v : ndarray  velocity components
        conv_u, conv_v : ndarray  convection terms −(u·∇)u
        mu : ndarray  dynamic viscosity (scalar or field)
        rho : ndarray  density field
        dt : float  timestep
        ccd : CCDSolver  differentiation operator
        buoy_v : ndarray, optional  buoyancy term for v-component
        psi : ndarray, optional  Heaviside interface field for band switching

        Returns
        -------
        u_star, v_star : ndarray  predicted velocity
        """


from .viscous_predictors import CNViscousPredictor, ExplicitViscousPredictor

__all__ = [
    "IViscousPredictor",
    "ExplicitViscousPredictor",
    "CNViscousPredictor",
]
