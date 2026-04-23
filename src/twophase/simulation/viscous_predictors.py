"""Concrete viscous predictor implementations.

Symbol mapping
--------------
u*, v* -> ``u_star``, ``v_star``
ρ -> ``rho``
μ -> ``mu``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .viscous_predictor import IViscousPredictor

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ns_terms.viscous import ViscousTerm
    from .scheme_build_ctx import ViscousBuildCtx


class ExplicitViscousPredictor(IViscousPredictor):
    """Forward-Euler explicit viscous predictor, O(Δt)."""

    scheme_names = ("explicit", "forward_euler")

    @classmethod
    def _build(cls, name: str, ctx: "ViscousBuildCtx") -> "ExplicitViscousPredictor":
        return cls(ctx.backend, ctx.re, ctx.spatial_scheme, ctx.viscous_term)

    def __init__(
        self,
        backend: "Backend",
        Re: float,
        spatial_scheme: str = "ccd_bulk",
        viscous_term: "ViscousTerm | None" = None,
    ) -> None:
        self.xp = backend.xp
        self.Re = Re
        if viscous_term is None:
            from ..ns_terms.viscous import ViscousTerm

            viscous_term = ViscousTerm(
                backend,
                Re=Re,
                cn_viscous=False,
                spatial_scheme=spatial_scheme,
            )
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
        psi: "array" | None = None,
    ) -> tuple["array", "array"]:
        """Explicit forward-Euler step."""
        visc_u, visc_v = self._viscous.compute_explicit([u, v], mu, rho, ccd, psi=psi)

        u_star = u + dt * (conv_u + visc_u)
        if buoy_v is not None:
            v_star = v + dt * (conv_v + visc_v + buoy_v)
        else:
            v_star = v + dt * (conv_v + visc_v)

        return u_star, v_star


class CNViscousPredictor(IViscousPredictor):
    """Crank-Nicolson implicit viscous predictor, O(Δt²)."""

    scheme_names = ("crank_nicolson",)
    _scheme_aliases = {"cn": "crank_nicolson", "crank-nicolson": "crank_nicolson"}

    @classmethod
    def _build(cls, name: str, ctx: "ViscousBuildCtx") -> "CNViscousPredictor":
        return cls(ctx.backend, ctx.viscous_term)

    def __init__(self, backend: "Backend", viscous_term: "ViscousTerm") -> None:
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
        psi: "array" | None = None,
    ) -> tuple["array", "array"]:
        """CN implicit step via ``ViscousTerm.apply_cn_predictor()``."""
        explicit_rhs = [rho * conv_u, rho * (conv_v + buoy_v if buoy_v is not None else conv_v)]
        vel_star = self._viscous.apply_cn_predictor(
            [u, v], explicit_rhs, mu, rho, ccd, dt, psi=psi
        )
        return vel_star[0], vel_star[1]
