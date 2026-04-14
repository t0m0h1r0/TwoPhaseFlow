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
import numpy as np
from typing import List, Optional, TYPE_CHECKING

from .interfaces import INSTerm

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend
    from ..time_integration.cn_advance import ICNAdvance


class ViscousTerm(INSTerm):
    """Compute the viscous stress divergence.

    Parameters
    ----------
    backend    : Backend
    Re         : Reynolds number
    cn_viscous : If True, use the CN strategy via ``cn_advance``.
                 If False, the caller is expected to use ``compute_explicit``
                 directly (see ``ns_terms/predictor.py``).
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
        cn_advance: Optional["ICNAdvance"] = None,
    ):
        self.xp = backend.xp
        self.Re = Re
        self.cn_viscous = cn_viscous
        # Lazy import breaks the cn_advance -> viscous typing cycle.
        if cn_advance is None:
            from ..time_integration.cn_advance import PicardCNAdvance
            cn_advance = PicardCNAdvance(backend)
        self.cn_advance = cn_advance

    # ── Explicit evaluation ───────────────────────────────────────────────

    def compute_explicit(
        self,
        velocity_components: List,
        mu: "array",
        rho: "array",
        ccd: "CCDSolver",
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
        return self._evaluate(velocity_components, mu, rho, ccd)

    # ── Crank-Nicolson predictor step ─────────────────────────────────────

    def apply_cn_predictor(
        self,
        u_old: List,
        explicit_rhs: List,
        mu: "array",
        rho: "array",
        ccd: "CCDSolver",
        dt: float,
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
            u_old, explicit_rhs, mu, rho, self, ccd, dt,
        )

    # ── Core evaluation ───────────────────────────────────────────────────

    def _stress_divergence_component(self, alpha: int, vel: List, mu, ccd: "CCDSolver"):
        """Compute Σ_β ∂[μ̃(∂u_α/∂x_β + ∂u_β/∂x_α)]/∂x_β for one α."""
        total = self.xp.zeros_like(vel[alpha])
        for beta in range(len(vel)):
            du_a_dbeta,  _ = ccd.differentiate(vel[alpha], beta)
            du_b_dalpha, _ = ccd.differentiate(vel[beta],  alpha)
            stress,          _ = ccd.differentiate(mu * (du_a_dbeta + du_b_dalpha), beta)
            total += stress
        return total

    def _evaluate(self, vel: List, mu, rho, ccd: "CCDSolver") -> List:
        """Compute ∇·[μ̃ (∇u + ∇uᵀ)] / (ρ̃ Re) for each component.

        Symmetric stress tensor S_{αβ} = μ̃ (∂u_α/∂x_β + ∂u_β/∂x_α) / 2
        Viscous force per unit volume for component α:
            V_α = (1/Re) Σ_β ∂[μ̃(∂u_α/∂x_β + ∂u_β/∂x_α)] / ∂x_β / ρ̃
        """
        ndim = len(vel)
        return [
            self._stress_divergence_component(alpha, vel, mu, ccd) / (self.Re * rho)
            for alpha in range(ndim)
        ]
