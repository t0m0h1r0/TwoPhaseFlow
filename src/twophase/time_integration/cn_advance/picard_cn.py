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

Paper trace: §7.4 eq:viscous_cn_helmholtz_v7 describes the implicit CN target
(I − γΔt L_ν)u* = RHS; this class implements the 1-step Picard (Heun
corrector) approximation, which is O(Δt²) but non-A-stable. The §7.4 warnbox
identifies this gap and §7 production stack uses IMEX-BDF2 (§7.3) instead.
"""
from __future__ import annotations
from typing import Callable, List, TYPE_CHECKING

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
        psi=None,
        intermediate_velocity_operator_transform: Callable[[List], None] | None = None,
        predictor_state_assembly: Callable[..., List] | None = None,
        convective_rhs: List | None = None,
        buoyancy_rhs: List | None = None,
    ) -> List:
        ndim = len(u_old)

        # Explicit viscous at time n
        visc_n = viscous_op._evaluate(u_old, mu, rho, ccd, psi=psi)

        # Forward-Euler predictor (evaluation point for the corrector)
        if predictor_state_assembly is not None:
            u_pred = predictor_state_assembly(
                u_old=u_old,
                explicit_rhs=explicit_rhs,
                convective_rhs=convective_rhs,
                buoyancy_rhs=buoyancy_rhs,
                visc_n=visc_n,
                rho=rho,
                dt=dt,
                xp=self.xp,
            )
        else:
            u_pred = [
                u_old[component_index]
                + dt * (explicit_rhs[component_index] / rho + visc_n[component_index])
                for component_index in range(ndim)
            ]
        u_pred_eval = u_pred
        if intermediate_velocity_operator_transform is not None:
            u_pred_eval = [self.xp.array(component, copy=True) for component in u_pred]
            intermediate_velocity_operator_transform(u_pred_eval)

        # Trapezoid corrector
        visc_star = viscous_op._evaluate(u_pred_eval, mu, rho, ccd, psi=psi)
        return [
            u_old[component_index]
            + dt * (
                explicit_rhs[component_index] / rho
                + 0.5 * visc_n[component_index]
                + 0.5 * visc_star[component_index]
            )
            for component_index in range(ndim)
        ]
