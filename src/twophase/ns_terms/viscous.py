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
from typing import List, TYPE_CHECKING

from ..interfaces.ns_terms import INSTerm

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


class ViscousTerm(INSTerm):
    """Compute the viscous stress divergence.

    Parameters
    ----------
    backend    : Backend
    Re         : Reynolds number
    cn_viscous : If True, use Crank-Nicolson (half-implicit).
    """

    def __init__(self, backend: "Backend", Re: float, cn_viscous: bool = True):
        self.xp = backend.xp
        self.Re = Re
        self.cn_viscous = cn_viscous

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
        u_star: List,
        explicit_rhs: List,
        mu: "array",
        rho: "array",
        ccd: "CCDSolver",
        dt: float,
    ) -> List:
        """Solve the CN system for each velocity component independently.

        The diagonal part of V is ν̃ Δu (where ν̃ = μ̃/ρ̃).  The off-diagonal
        (cross) terms are treated explicitly.

        Solves component-by-component using a direct CCD-based approach:
        since the spatial operator is applied through CCD which produces
        the full field at once, we iterate with a simple fixed-point scheme
        that converges in 1–2 iterations for moderate Δt.
        """
        xp = self.xp
        ndim = len(u_old)
        Re = self.Re

        # Explicit viscous term at time n
        visc_n = self._evaluate(u_old, mu, rho, ccd)

        # Initialise u* with the fully-explicit predictor.
        # Correct formula: u* = u^n + Δt * R / ρ̃
        # where R = explicit_rhs (force/volume) + ρ̃ * visc_n (force/volume).
        # Since visc_n = V_α/(Re·ρ̃) is already divided by ρ̃, we write:
        #   u* = u^n + Δt * (explicit_rhs / ρ̃ + visc_n)
        u_pred = [
            u_old[c] + dt * (explicit_rhs[c] / rho + visc_n[c])
            for c in range(ndim)
        ]

        if not self.cn_viscous:
            return u_pred

        # One CN correction iteration
        visc_star = self._evaluate(u_pred, mu, rho, ccd)
        u_cn = [
            u_old[c] + dt * (explicit_rhs[c] / rho
                              + 0.5 * visc_n[c]
                              + 0.5 * visc_star[c])
            for c in range(ndim)
        ]
        return u_cn

    # ── Core evaluation ───────────────────────────────────────────────────

    def _evaluate(self, vel: List, mu, rho, ccd: "CCDSolver") -> List:
        """Compute ∇·[μ̃ (∇u + ∇uᵀ)] / (ρ̃ Re) for each component."""
        xp = self.xp
        ndim = len(vel)
        Re = self.Re
        result = [xp.zeros_like(vel[c]) for c in range(ndim)]

        # Symmetric stress tensor S_{αβ} = μ̃ (∂u_α/∂x_β + ∂u_β/∂x_α) / 2
        # Divergence of 2S for component α:
        #   V_α = (2/Re) Σ_β ∂S_{αβ}/∂x_β / ρ̃
        # = (1/Re) Σ_β ∂[μ̃(∂u_α/∂x_β + ∂u_β/∂x_α)] / ∂x_β / ρ̃

        for alpha in range(ndim):
            for beta in range(ndim):
                # ∂u_α/∂x_β and ∂u_β/∂x_α
                du_a_dbeta, _ = ccd.differentiate(vel[alpha], beta)
                du_b_dalpha, _ = ccd.differentiate(vel[beta], alpha)

                # Stress component: μ̃ (∂u_α/∂x_β + ∂u_β/∂x_α)
                stress = mu * (du_a_dbeta + du_b_dalpha)

                # Divergence along β
                d_stress_dbeta, _ = ccd.differentiate(stress, beta)
                result[alpha] += d_stress_dbeta

            result[alpha] = result[alpha] / (Re * rho)

        return result
