"""
CFL time-step calculator.

Implements §8 (Eq. 84) of the paper.

Active constraints depend on viscous treatment (§8 stability warnbox):

    Convective CFL:  Δt ≤ CFL · h / |u|_max           (always active)
    Capillary CFL:   Δt ≤ sqrt((ρ_l+ρ_g) h³ / (2π σ)) (§8.4 Eq.(dt_sigma))
    Viscous CFL:     Δt ≤ CFL · h² / (4 ν_max)         (explicit viscous only)

The viscous CFL is OMITTED when Crank-Nicolson viscous treatment is used
(cn_viscous=True, the default), because CN is unconditionally stable and
does not impose a parabolic time-step restriction.

where ν_max = max(μ̃)/min(ρ̃) is the maximum kinematic viscosity.
In the dimensionless formulation (ρ_l=1, σ=1/We):
    Δt_σ = sqrt((1 + ρ̃_g) · We · h³ / (2π))

The overall Δt is the minimum of all active bounds.
A hard minimum Δt_min = 1e-8 prevents stalling.
"""

from __future__ import annotations
import math
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid


class CFLCalculator:
    """Compute a stable time step satisfying all CFL conditions.

    Parameters
    ----------
    backend    : Backend
    grid       : Grid
    cfl_number : safety factor (< 1)
    We         : Weber number (for capillary wave CFL).  None disables the
                 capillary constraint (backward-compatible default).
    rho_ratio  : ρ_gas / ρ_liquid (for capillary wave CFL, default 0.0).
    cn_viscous : If True (default), viscous CFL is omitted — CN is
                 unconditionally stable (§8 stability warnbox).
                 If False, viscous CFL is included for explicit treatment.
    """

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        cfl_number: float,
        We: Optional[float] = None,
        rho_ratio: float = 0.0,
        cn_viscous: bool = True,
    ):
        self.xp = backend.xp
        self.grid = grid
        self.cfl = cfl_number
        # Minimum cell spacing (for CFL denominator)
        self._h_min = min(
            float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)
        )
        # Pre-compute capillary wave time-step bound (§8.4 Eq.(dt_sigma)):
        #   Δt_σ = sqrt((ρ_l + ρ_g) · h³ / (2π · σ))
        # Dimensionless: ρ_l = 1, σ = 1/We  ⟹  Δt_σ = sqrt((1+rho_ratio)·We·h³/(2π))
        if We is not None and We > 0.0:
            h3 = self._h_min ** 3
            self._dt_sigma = math.sqrt((1.0 + rho_ratio) * We * h3 / (2.0 * math.pi))
        else:
            self._dt_sigma = None   # capillary constraint disabled
        self._cn_viscous = cn_viscous

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

        dt = dt_conv

        # Viscous CFL — only for explicit viscous treatment (§8 stability warnbox).
        # Omitted when cn_viscous=True (CN is unconditionally stable).
        if not self._cn_viscous:
            nu_max = float(xp.max(mu / rho))
            nu_max = max(nu_max, 1e-14)
            dt_visc = cfl * h * h / (4.0 * nu_max)
            dt = min(dt, dt_visc)

        # Capillary wave CFL (§8.4 Eq.(dt_sigma))
        if self._dt_sigma is not None:
            dt = min(dt, self._dt_sigma)

        return max(dt, 1e-8)
