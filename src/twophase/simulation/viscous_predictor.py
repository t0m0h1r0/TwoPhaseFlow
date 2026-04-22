"""Viscous predictor strategy (CN vs Explicit Euler).

Encapsulates the choice between:
- ExplicitViscousPredictor: forward-Euler, O(Δt)
- CNViscousPredictor: Crank-Nicolson with iterative solver, O(Δt²)

Both implement IViscousPredictor with the same signature.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import ClassVar, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ns_terms.viscous import ViscousTerm
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

        Returns
        -------
        u_star, v_star : ndarray  predicted velocity
        """


class ExplicitViscousPredictor(IViscousPredictor):
    """Forward-Euler explicit viscous predictor, O(Δt).

    u* = u + Δt (convection + viscous)
    v* = v + Δt (convection + buoyancy + viscous)

    No implicit solve; Reynolds-number-constrained CFL.
    """

    scheme_names = ("explicit", "forward_euler")

    @classmethod
    def _build(cls, name: str, ctx: "ViscousBuildCtx") -> "ExplicitViscousPredictor":
        return cls(ctx.backend, ctx.re)

    def __init__(self, backend: "Backend", Re: float) -> None:
        self.xp = backend.xp
        self.Re = Re

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
    ) -> tuple["array", "array"]:
        """Explicit forward-Euler step."""
        # Compute Laplacian terms (second derivatives)
        du_xx, _ = ccd.differentiate(u, 0)
        du_xx, _ = ccd.differentiate(du_xx, 0)
        du_yy, _ = ccd.differentiate(u, 1)
        du_yy, _ = ccd.differentiate(du_yy, 1)

        dv_xx, _ = ccd.differentiate(v, 0)
        dv_xx, _ = ccd.differentiate(dv_xx, 0)
        dv_yy, _ = ccd.differentiate(v, 1)
        dv_yy, _ = ccd.differentiate(dv_yy, 1)

        # Viscous term: (mu / rho) * (∂²u/∂x² + ∂²u/∂y²)
        visc_u = (mu / rho) * (du_xx + du_yy)
        visc_v = (mu / rho) * (dv_xx + dv_yy)

        # Advance velocity
        u_star = u + dt * (conv_u + visc_u)
        if buoy_v is not None:
            v_star = v + dt * (conv_v + visc_v + buoy_v)
        else:
            v_star = v + dt * (conv_v + visc_v)

        return u_star, v_star


class CNViscousPredictor(IViscousPredictor):
    """Crank-Nicolson implicit viscous predictor, O(Δt²).

    Delegates to ViscousTerm.apply_cn_predictor() which uses an iterative
    CN time-advance strategy (Picard, Newton, GMRES, etc.).

    Requires solving a linear system for each velocity component.
    """

    scheme_names     = ("crank_nicolson",)
    _scheme_aliases  = {"cn": "crank_nicolson", "crank-nicolson": "crank_nicolson"}

    @classmethod
    def _build(cls, name: str, ctx: "ViscousBuildCtx") -> "CNViscousPredictor":
        return cls(ctx.backend, ctx.viscous_term)

    def __init__(self, backend: "Backend", viscous_term: "ViscousTerm") -> None:
        """

        Parameters
        ----------
        backend : Backend
        viscous_term : ViscousTerm
            Viscous term operator with cn_advance strategy.
        """
        self.xp = backend.xp
        self._viscous = viscous_term

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
    ) -> tuple["array", "array"]:
        """CN implicit step via ViscousTerm.apply_cn_predictor()."""
        # Construct explicit RHS: rho * (convection + buoyancy)
        explicit_rhs = [rho * conv_u, rho * (conv_v + buoy_v if buoy_v is not None else conv_v)]

        # Delegate to CN solver
        vel_star = self._viscous.apply_cn_predictor(
            [u, v], explicit_rhs, mu, rho, ccd, dt,
        )

        return vel_star[0], vel_star[1]
