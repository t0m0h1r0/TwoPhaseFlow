"""
Viscous term: (1/Re) ∇·[μ̃ (∇u + ∇uᵀ)] / ρ̃.

Implements §9 of the paper.  In the non-dimensional one-fluid formulation
the full strain-rate tensor divergence is (§2.4):

    V_α = (1/Re) Σ_β ∂/∂x_β [μ̃ (∂u_α/∂x_β + ∂u_β/∂x_α)] / ρ̃

For a nearly-incompressible flow (∇·u ≈ 0) this simplifies to:

    V_α ≈ (1/(Re ρ̃)) [∇·(μ̃ ∇u_α) + Σ_β ∂/∂x_β (μ̃ ∂u_β/∂x_α)]

which is what is implemented here.

Crank-Nicolson (CN) half-implicit treatment (§9, ``cn_viscous=True``):

The CN scheme requires solving for u* implicitly:

    ρ (u* − uⁿ) / Δt = ½ V(u*) + ½ V(uⁿ) + explicit_terms

Rearranging for each component α:

    [ρ/Δt − ½ V_lin] u*_α = ρ uⁿ_α / Δt + ½ V(uⁿ)_α + explicit

where V_lin u_α = (1/Re) ∇·(μ̃ ∇u_α) is the linear part.

The non-linear cross-term Σ_{β≠α} ∂/∂x_β (μ̃ ∂u_β/∂x_α) is treated
explicitly at time n for simplicity (standard practice).

When ``cn_viscous=False`` the term is evaluated explicitly and simply
returned as an array.
"""

from __future__ import annotations
from typing import Callable, List, Optional, TYPE_CHECKING

from .interfaces import INSTerm
from .viscous_spatial import (
    ViscousSpatialEvaluator,
    canonical_viscous_spatial_scheme,
)

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend
    from ..time_integration.cn_advance import ICNAdvance
    from .context import NSComputeContext


class ViscousTerm(INSTerm):
    """Compute the viscous stress divergence.

    Parameters
    ----------
    backend    : Backend
    Re         : Reynolds number
    cn_viscous : If True, use the CN strategy via ``cn_advance``.
                 If False, the caller is expected to use ``compute_explicit``
                 directly (see ``ns_terms/predictor.py``).
    spatial_scheme : Spatial operator for the stress-divergence body.
                 ``ccd``/``ccd_bulk`` uses CCD for Layer-A velocity gradients and
                 low-order physical-coordinate stress divergence.
                 ``conservative_stress`` uses low-order gradients everywhere.
                 ``ccd_stress_legacy`` preserves the old all-CCD
                 stress/divergence path.
    cn_advance : CN time-advance strategy (Strategy pattern). When None,
                 defaults to ``PicardCNAdvance`` — the canonical production
                 behaviour. See ``cn_advance/`` subpackage and
                 ``docs/memo/extended_cn_impl_design.md``.
    """

    def __init__(
        self,
        backend: "Backend",
        Re: float,
        cn_viscous: bool = True,
        spatial_scheme: str = "ccd_bulk",
        cn_advance: Optional["ICNAdvance"] = None,
    ):
        self.xp = backend.xp
        self.Re = Re
        self.cn_viscous = cn_viscous
        self.spatial_scheme = self._canonical_spatial_scheme(spatial_scheme)
        self._spatial_evaluator = ViscousSpatialEvaluator(self.xp, self.Re)
        # Lazy import breaks the cn_advance -> viscous typing cycle.
        if cn_advance is None:
            from ..time_integration.cn_advance import PicardCNAdvance
            cn_advance = PicardCNAdvance(backend)
        self.cn_advance = cn_advance

    # ── INSTerm interface ────────────────────────────────────────────────

    def compute(self, ctx: "NSComputeContext") -> List:
        """Compute viscous term via explicit evaluation (Interface implementation).

        Parameters
        ----------
        ctx : NSComputeContext
            Context with velocity, ccd, rho, mu

        Returns
        -------
        List[ndarray]
            Viscous stress per velocity component
        """
        return self.compute_explicit(ctx.velocity, ctx.mu, ctx.rho, ctx.ccd)

    # ── Explicit evaluation ───────────────────────────────────────────────

    def compute_explicit(
        self,
        velocity_components: List,
        mu: "array",
        rho: "array",
        ccd: "CCDSolver",
        psi=None,
    ) -> List:
        """Return V_α = (1/Re) ∇·[μ̃ (∇u + ∇uᵀ)] / ρ̃ evaluated at current u.

        Parameters
        ----------
        velocity_components : [u, v[, w]]
        mu                  : dynamic viscosity field
        rho                 : density field
        ccd                 : CCDSolver

        Returns
        -------
        visc : list of arrays, one per velocity component
        """
        return self._evaluate(velocity_components, mu, rho, ccd, psi=psi)

    # ── Crank-Nicolson predictor step ─────────────────────────────────────

    def apply_cn_predictor(
        self,
        u_old: List,
        explicit_rhs: List,
        mu: "array",
        rho: "array",
        ccd: "CCDSolver",
        dt: float,
        psi=None,
        intermediate_velocity_operator_transform: Callable[[List], None] | None = None,
        predictor_state_assembly: Callable[..., List] | None = None,
        convective_rhs: List | None = None,
        buoyancy_rhs: List | None = None,
    ) -> List:
        """Delegate the viscous predictor advance to ``self.cn_advance``.

        The strategy pattern separates the *operator* V(u) (owned here) from
        the *temporal discretization* (owned by the strategy). See
        ``cn_advance/`` subpackage for available strategies and
        ``docs/memo/extended_cn_impl_design.md`` for rationale.

        When ``self.cn_viscous`` is False this method falls back to a plain
        forward-Euler step — preserved for API completeness though the
        production caller in ``ns_terms/predictor.py`` guards the CN branch
        on ``config.numerics.cn_viscous`` and so never triggers the fallback
        via this entrypoint.
        """
        if not self.cn_viscous:
            # Dead fast-path: explicit Euler using V(u^n). Bit-exact with
            # the pre-Phase-1 behaviour.
            visc_n = self._evaluate(u_old, mu, rho, ccd)
            return [
                u_old[c] + dt * (explicit_rhs[c] / rho + visc_n[c])
                for c in range(len(u_old))
            ]
        return self.cn_advance.advance(
            u_old,
            explicit_rhs,
            mu,
            rho,
            self,
            ccd,
            dt,
            psi=psi,
            intermediate_velocity_operator_transform=intermediate_velocity_operator_transform,
            predictor_state_assembly=predictor_state_assembly,
            convective_rhs=convective_rhs,
            buoyancy_rhs=buoyancy_rhs,
        )

    # ── Core evaluation ───────────────────────────────────────────────────

    @staticmethod
    def _canonical_spatial_scheme(name: str) -> str:
        return canonical_viscous_spatial_scheme(name)

    def _evaluate(self, vel: List, mu, rho, ccd: "CCDSolver", psi=None) -> List:
        """Compute ∇·[μ̃ (∇u + ∇uᵀ)] / (ρ̃ Re) for each component.

        Symmetric stress tensor S_{αβ} = μ̃ (∂u_α/∂x_β + ∂u_β/∂x_α) / 2
        Viscous force per unit volume for component α:
            V_α = (1/Re) Σ_β ∂[μ̃(∂u_α/∂x_β + ∂u_β/∂x_α)] / ∂x_β / ρ̃
        """
        return self._spatial_evaluator.evaluate(
            self.spatial_scheme,
            vel,
            mu,
            rho,
            ccd,
            psi=psi,
        )
