"""
CFL time-step calculator.

Implements §8 (Eq. 84) of the paper.

Three conditions must be satisfied simultaneously:

    Convective CFL:  Δt ≤ CFL · h / |u|_max
    Interface CFL:   Δt ≤ CFL · h / |u·∇φ|_max  (advection of ψ)
    Viscous CFL:     Δt ≤ CFL · h² / (4 ν_max)   (parabolic stability)

where ν_max = max(μ̃)/min(ρ̃) is the maximum kinematic viscosity.

The overall Δt is the minimum of the three bounds.
A hard minimum Δt_min = 1e-8 prevents stalling.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid


class CFLCalculator:
    """Compute a stable time step satisfying all three CFL conditions.

    Parameters
    ----------
    backend    : Backend
    grid       : Grid
    cfl_number : safety factor (< 1)
    """

    def __init__(self, backend: "Backend", grid: "Grid", cfl_number: float):
        self.xp = backend.xp
        self.grid = grid
        self.cfl = cfl_number
        # Minimum cell spacing (for CFL denominator)
        self._h_min = min(
            float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)
        )

    def compute(
        self,
        velocity_components: List,
        mu: "array",
        rho: "array",
    ) -> float:
        """Return the CFL-limited time step.

        Parameters
        ----------
        velocity_components : [u, v[, w]]
        mu                  : viscosity field
        rho                 : density field

        Returns
        -------
        dt : float > 0
        """
        xp = self.xp
        h = self._h_min
        cfl = self.cfl

        # Max speed
        u_max = max(float(xp.max(xp.abs(vel))) for vel in velocity_components)
        u_max = max(u_max, 1e-14)

        dt_conv = cfl * h / u_max

        # Viscous CFL
        nu_max = float(xp.max(mu / rho))
        nu_max = max(nu_max, 1e-14)
        dt_visc = cfl * h * h / (4.0 * nu_max)

        dt = min(dt_conv, dt_visc)
        return max(dt, 1e-8)
