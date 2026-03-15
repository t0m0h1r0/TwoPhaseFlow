"""
Velocity predictor step (u* computation).

Implements Step 5 of the full algorithm (§9.1 Eq. 85–92).

The predictor solves:

    ρ̃^{n+1} (u* − uⁿ) / Δt = R^{n+1}

where the RHS collects:

    R = −ρ̃ (u·∇)u                    (convection, explicit)
      + (1/Re) ∇·[μ̃ (∇u+∇uᵀ)]        (viscous, CN or explicit)
      − ρ̃ ẑ / Fr²                     (gravity, explicit)
      + κ ∇ψ / We                     (surface tension, at t^{n+1})

The predictor does NOT enforce ∇·u* = 0; that is handled by the pressure
Poisson equation and the corrector step.

When ``cn_viscous=True`` the viscous term uses the Crank-Nicolson scheme
(§9), which performs one fixed-point iteration:
  1. Compute explicit u* with V(uⁿ).
  2. Evaluate V(u*) and recompute with the average ½[V(uⁿ)+V(u*)].
"""

from __future__ import annotations
import numpy as np
from typing import List, TYPE_CHECKING

from .convection import ConvectionTerm
from .viscous import ViscousTerm
from .gravity import GravityTerm
from .surface_tension import SurfaceTensionTerm

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend
    from ..config import SimulationConfig


class Predictor:
    """Assemble all NS RHS terms and advance u → u*.

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig
    """

    def __init__(self, backend: "Backend", config: "SimulationConfig"):
        self.xp = backend.xp
        self.config = config

        self.convection    = ConvectionTerm(backend)
        self.viscous       = ViscousTerm(backend, config.Re, config.cn_viscous)
        self.gravity       = GravityTerm(backend, config.Fr, config.ndim)
        self.surface_tens  = SurfaceTensionTerm(backend, config.We)

    def compute(
        self,
        vel_n: List,
        rho: "array",
        mu: "array",
        kappa: "array",
        psi: "array",
        ccd: "CCDSolver",
        dt: float,
    ) -> List:
        """Compute u* = uⁿ + Δt * R / ρ̃.

        Parameters
        ----------
        vel_n  : velocity components [u, v[, w]] at time n
        rho    : density at time n+1
        mu     : viscosity at time n+1
        kappa  : curvature at time n+1
        psi    : CLS field at time n+1
        ccd    : CCDSolver
        dt     : time step

        Returns
        -------
        vel_star : list of u* arrays
        """
        xp = self.xp

        # ── Explicit terms ────────────────────────────────────────────────
        conv = self.convection.compute(vel_n, ccd)           # −(u·∇)u  (ρ-weighted later)
        grav = self.gravity.compute(rho, vel_n[0].shape)     # −ρ̃ ẑ/Fr²
        st   = self.surface_tens.compute(kappa, psi, ccd)    # κ ∇ψ/We

        # ── Combine explicit terms (per component) ────────────────────────
        # Multiply convection by ρ̃ (because it enters as ρ̃ a_conv = −ρ̃(u·∇)u)
        explicit_rhs = [
            rho * conv[c] + grav[c] + st[c]
            for c in range(self.config.ndim)
        ]

        # ── Viscous term (CN or explicit) ─────────────────────────────────
        if self.config.cn_viscous:
            vel_star = self.viscous.apply_cn_predictor(
                vel_n, None, explicit_rhs, mu, rho, ccd, dt
            )
        else:
            visc = self.viscous.compute_explicit(vel_n, mu, rho, ccd)
            vel_star = [
                vel_n[c] + dt * (explicit_rhs[c] + rho * visc[c]) / rho
                for c in range(self.config.ndim)
            ]

        return vel_star
