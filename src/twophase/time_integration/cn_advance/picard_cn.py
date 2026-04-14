"""
PicardCNAdvance — 1-step Picard iteration on the CN equation.

Algebraically equivalent to Heun's predictor-corrector (explicit trapezoid):

    u_pred = u^n + dt * (explicit_rhs/rho + V(u^n))                       # FE
    u_star = u^n + dt * (explicit_rhs/rho + 0.5*V(u^n) + 0.5*V(u_pred))  # trap

Accuracy : O(dt^2)
Stability: NOT unconditionally stable -- this is a fully explicit evaluation
           of V at u^n and u_pred, so a parabolic (viscous) CFL condition
           Δt ≲ h²/(4 ν_max) is formally required. In production the
           convective and capillary CFL dominate so this has not been the
           binding constraint, but the cfl.py module docstring makes the
           caveat explicit.

This is the canonical legacy behaviour preserved bit-exactly as the default
strategy under the Extended CN strategy pattern. True implicit CN (A-stable)
and Padé-(2,2) variants arrive in later phases. See
docs/memo/extended_cn_impl_design.md §5.1 for the extraction rationale and
PR-5 bit-exact regression plan.
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...ns_terms.viscous import ViscousTerm
    from ...ccd.ccd_solver import CCDSolver
    from ...backend import Backend


class PicardCNAdvance:
    """1-step Picard on CN (Heun predictor-corrector)."""

    def __init__(self, backend: "Backend"):
        self.xp = backend.xp

    def advance(
        self,
        u_old: List,
        explicit_rhs: List,
        mu,
        rho,
        viscous_op: "ViscousTerm",
        ccd: "CCDSolver",
        dt: float,
    ) -> List:
        ndim = len(u_old)

        # Explicit viscous at time n
        visc_n = viscous_op._evaluate(u_old, mu, rho, ccd)

        # Forward-Euler predictor (evaluation point for the corrector)
        u_pred = [
            u_old[c] + dt * (explicit_rhs[c] / rho + visc_n[c])
            for c in range(ndim)
        ]

        # Trapezoid corrector
        visc_star = viscous_op._evaluate(u_pred, mu, rho, ccd)
        return [
            u_old[c] + dt * (explicit_rhs[c] / rho
                             + 0.5 * visc_n[c]
                             + 0.5 * visc_star[c])
            for c in range(ndim)
        ]
