"""
RichardsonCNAdvance — Richardson-extrapolated CN advance.

Given a base ICNAdvance strategy Φ(Δt) whose error expansion starts at
O(Δt^2), the Richardson combination

    u^{n+1}  =  (4·Φ(Δt/2)∘Φ(Δt/2) − Φ(Δt)) / 3

annihilates the O(Δt^2) error term and yields O(Δt^4) accuracy without
modifying Φ internally. Because Φ is treated as a black box, this lifts
*every* Δt-dependent piece of the base step simultaneously — diagonal
viscous, explicit cross-terms, and the frozen explicit_rhs — solving the
cross-term order-cap trap documented in
docs/memo/extended_cn_impl_design.md §2 (point 6) and §5.2.

Properties
----------
  Order (general base): +1 over the base. Richardson extrapolation
             annihilates the leading term of the error expansion, gaining
             exactly one order for a *generic* O(Δt^p) method.
  Order (symmetric base): +2 over the base. When the base is a *symmetric*
             one-step method (trapezoidal rule = true implicit CN / midpoint /
             Padé-(2,2)), its error expansion contains only even powers of
             Δt, and annihilating the leading even term lifts the order by 2.
  Stability: inherits from the base. Wrapping Picard yields an explicit
             scheme with the same CFL floor; wrapping Implicit CN or
             Padé-(2,2) yields A-stable schemes.
  Cost     : ~3× base (one big step + two half steps) per outer call.

  Concrete orders for strategies in this package:
    RichardsonCNAdvance(PicardCNAdvance)  →  O(Δt^3)
        (Picard is Heun = explicit 2-stage RK, non-symmetric; +1 gain.)
    RichardsonCNAdvance(ImplicitCNAdvance)  →  O(Δt^4)         [Phase 3]
        (true trapezoidal rule is symmetric; +2 gain.)
    RichardsonCNAdvance(Pade22CNAdvance)    →  O(Δt^6)         [Phase 6]
        (Padé-(2,2) rational approximant R(z) is symmetric; +2 gain.)

Caveats
-------
  explicit_rhs is evaluated at time n by the caller (ns_terms/predictor.py)
  and held constant across the Richardson substeps. This matches the
  ordinary Richardson-on-substep convention and does not degrade the
  extrapolation order, because the substep fields all see the same rhs
  function of Δt. The AB2 convective contribution inside explicit_rhs is
  itself only O(Δt^2) accurate; the global ns_pipeline temporal order is
  therefore still capped at 2 unless AB2 is also upgraded. Extended-CN
  Richardson specifically raises the *viscous step* to O(Δt^4), which
  matters on viscous-dominated manufactured-solution verification.

See docs/memo/extended_cn_impl_design.md §5.2 and WIKI-T-033 §5.2 / §6.
"""
from __future__ import annotations
from typing import Callable, List, TYPE_CHECKING

from .base import ICNAdvance

if TYPE_CHECKING:
    from ...ns_terms.viscous import ViscousTerm
    from ...ccd.ccd_solver import CCDSolver


class RichardsonCNAdvance:
    """Richardson (4 u_{Δt/2,2} − u_Δt)/3 extrapolation wrapping a base strategy."""

    def __init__(self, base: ICNAdvance):
        self.base = base

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
        advance_kwargs = {
            "psi": psi,
            "intermediate_velocity_operator_transform": intermediate_velocity_operator_transform,
            "predictor_state_assembly": predictor_state_assembly,
            "convective_rhs": convective_rhs,
            "buoyancy_rhs": buoyancy_rhs,
        }
        # Big step
        u1 = self.base.advance(
            u_old, explicit_rhs, mu, rho, viscous_op, ccd, dt, **advance_kwargs,
        )

        # Two half steps, explicit_rhs frozen at time n (matches the
        # surrounding IPC+AB2 assembly in ns_terms/predictor.py).
        dt_half = 0.5 * dt
        u_half = self.base.advance(
            u_old, explicit_rhs, mu, rho, viscous_op, ccd, dt_half, **advance_kwargs,
        )
        u2 = self.base.advance(
            u_half, explicit_rhs, mu, rho, viscous_op, ccd, dt_half, **advance_kwargs,
        )

        # Extrapolation: (4·u_{Δt/2,2} − u_Δt) / 3
        return [
            (4.0 * u2[component_index] - u1[component_index]) / 3.0
            for component_index in range(len(u_old))
        ]
