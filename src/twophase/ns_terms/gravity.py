"""
Gravity (body force) term: −ẑ / Fr².

Implements §9 (Eq. 85) of the paper.

The dimensionless body force is:

    g = −ẑ / Fr²

where ẑ is the unit vector in the direction of gravity (last spatial axis
by convention: y in 2-D, z in 3-D) and Fr = U/sqrt(gL) is the Froude number.

Note: ρ̃ cancels in the momentum equation because gravity already appears
as ρ̃ g on the right-hand side:

    ρ̃ Du/Dt = ⋯ − ρ̃ ẑ / Fr²

so the acceleration contributed to the predictor step is:

    a_gravity = −ẑ / Fr²   (multiplied by ρ̃ comes from the left-hand side)

This implementation returns the body-force acceleration (not the force),
consistent with the predictor in predictor.py which adds (dt/ρ̃) * F_body.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from ..interfaces.ns_terms import INSTerm

if TYPE_CHECKING:
    from ..backend import Backend


class GravityTerm(INSTerm):
    """Gravity acceleration −ẑ / Fr².

    Parameters
    ----------
    backend : Backend
    Fr      : Froude number
    ndim    : spatial dimension (gravity acts on the last axis)
    """

    def __init__(self, backend: "Backend", Fr: float, ndim: int):
        self.xp = backend.xp
        self.Fr = Fr
        self.ndim = ndim
        # Gravity axis: last spatial axis (y in 2-D, z in 3-D)
        self.grav_axis = ndim - 1

    def compute(self, rho, vel_shape) -> List:
        """Return the gravitational acceleration for each velocity component.

        Parameters
        ----------
        rho       : density field, shape ``grid.shape``
        vel_shape : shape of a single velocity component (= grid.shape)

        Returns
        -------
        grav : list of arrays, one per dimension.
               All-zero except the gravity axis which contains −ρ̃/Fr².
        """
        xp = self.xp
        grav = [xp.zeros(vel_shape) for _ in range(self.ndim)]
        # Gravity force on velocity: ρ̃ a = ρ̃ (−ẑ/Fr²)
        # Predictor adds (Δt / ρ̃) * (ρ̃ * grav_acc) = Δt * grav_acc,
        # so we store the force density (ρ̃ * g_acc):
        grav[self.grav_axis] = -rho / (self.Fr ** 2)
        return grav
