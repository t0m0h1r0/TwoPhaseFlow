"""
ICNAdvance — Protocol for viscous predictor time-advance strategies.

See docs/memo/extended_cn_impl_design.md §4 for the interface contract and
the rationale for the strategy pattern separation (SRP + DIP, C1 SOLID).
"""
from __future__ import annotations
from typing import List, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from ...ns_terms.viscous import ViscousTerm
    from ...ccd.ccd_solver import CCDSolver


class ICNAdvance(Protocol):
    """Viscous predictor time-advance strategy.

    Given u^n, an explicit force/volume RHS at time n, and the viscous
    operator V(u), return u* (the velocity field after the viscous
    predictor step) such that — in the strategy-specific sense —

        rho * (u* - u^n) / dt  ~=  explicit_rhs
                               + temporal_discretization(V, u^n, u*, dt)

    Strategies currently defined:
      - PicardCNAdvance : 1-step Picard on CN (Heun), O(dt^2), conditional
                          stability.
    Strategies planned (see the design memo):
      - RichardsonCNAdvance, ImplicitCNAdvance, Pade22CNAdvance.

    Parameters
    ----------
    u_old        : velocity at time n, list of arrays (len = ndim)
    explicit_rhs : force/volume RHS at time n (grad p, gravity, surface
                   tension, convective AB2), list of arrays
    mu, rho      : viscosity and density fields
    viscous_op   : ViscousTerm instance providing V(u) via ``_evaluate``
    ccd          : CCDSolver
    dt           : time step

    Returns
    -------
    u_star : list of arrays, predicted velocity after the viscous step
    """

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
    ) -> List: ...
