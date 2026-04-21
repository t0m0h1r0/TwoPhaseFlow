"""Level-set transport strategy (advection + reinit + redistancing).

Encapsulates two distinct paths:
1. PhiPrimaryTransport — logit-space advection (φ) + mass correction
2. PsiDirectTransport — direct ψ advection + optional reinit

Both implement ILevelSetTransport.advance(psi, velocity, dt, step_index) -> psi
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

import numpy as np

from .heaviside import apply_mass_correction

if TYPE_CHECKING:
    from ..backend import Backend
    from .reconstruction import HeavisideInterfaceReconstructor
    from .advection import DissipativeCCDAdvection
    from . interfaces import ILevelSetAdvection, IReinitializer


class ILevelSetTransport(ABC):
    """Abstract interface for level-set transport (advection + reinit + redistancing).

    The two branches of step() — phi-primary vs direct psi advection — differ in
    algorithm but share a common interface: both take psi and return psi_new.
    """

    @abstractmethod
    def advance(
        self,
        psi: np.ndarray,
        velocity: List[np.ndarray],
        dt: float,
        step_index: int = 0,
    ) -> np.ndarray:
        """Advance the level-set by one timestep.

        Parameters
        ----------
        psi : ndarray
            Conservative level-set (1 = liquid, 0 = gas)
        velocity : list of ndarray
            [u, v] or [u, v, w] velocity components
        dt : float
            Timestep
        step_index : int
            Timestep counter (used for redistancing cadence)

        Returns
        -------
        psi_new : ndarray
            Updated level-set
        """


class StaticInterfaceTransport(ILevelSetTransport):
    """No-op transport for frozen-interface diagnostics/reference runs."""

    def __init__(self, backend: "Backend"):
        self.xp = backend.xp

    def advance(
        self,
        psi: np.ndarray,
        velocity: List[np.ndarray],
        dt: float,
        step_index: int = 0,
    ) -> np.ndarray:
        return self.xp.asarray(psi)


class PhiPrimaryTransport(ILevelSetTransport):
    """Phi-primary transport: logit-space advection + mass correction.

    Flow:
    1. φ = logit(ψ) — signed-distance equivalent
    2. Advect φ via chosen scheme (DCCD/FCCD)
    3. Clip φ to valid range
    4. ψ = logit^{-1}(φ) — back to Heaviside
    5. Periodically redistribute (reinitialize) to correct thickness
    6. Apply mass correction to restore initial volume
    """

    def __init__(
        self,
        backend: "Backend",
        phi_primary_params: dict,
        reconstruct_phi_primary: "HeavisideInterfaceReconstructor",
        advection: "ILevelSetAdvection",
        reinitializer: "IReinitializer",
        grid,
    ):
        """
        Parameters
        ----------
        backend : Backend
        phi_primary_params : dict
            Keys: redist_every, clip_factor, eps_scale
        reconstruct_phi_primary : HeavisideInterfaceReconstructor
        advection : ILevelSetAdvection
        reinitializer : IReinitializer
        grid : Grid
        """
        self.xp = backend.xp
        self.backend = backend
        self.reconstruct = reconstruct_phi_primary
        self.advection = advection
        self.reinitializer = reinitializer
        self.grid = grid

        self.redist_every = max(1, int(phi_primary_params.get("redist_every", 4)))
        self.clip_factor = max(2.0, float(phi_primary_params.get("clip_factor", 12.0)))
        self.eps_scale = max(1.0, float(phi_primary_params.get("eps_scale", 1.0)))

    def advance(
        self,
        psi: np.ndarray,
        velocity: List[np.ndarray],
        dt: float,
        step_index: int = 0,
    ) -> np.ndarray:
        """Phi-primary transport with periodic redistancing."""
        xp = self.xp

        # Pre-advection mass snapshot
        dV_pre = self.grid.cell_volumes()
        M_pre = xp.sum(psi * dV_pre)

        # Transform ψ → φ (logit space)
        phi = self.reconstruct.phi_from_psi(psi)

        # Advect φ in logit space
        phi = self.advection.advance(phi, velocity, dt, clip_bounds=None)

        # Clip φ to valid range
        phi = self.reconstruct.clip_phi(phi)

        # Transform back ψ = logit^{-1}(φ)
        psi = self.reconstruct.psi_from_phi(phi)

        # Periodic redistancing to correct interface thickness
        if step_index > 0 and (step_index % self.redist_every == 0):
            psi = self.reinitializer.reinitialize(psi)
            phi = self.reconstruct.phi_from_psi(psi)
            psi = self.reconstruct.psi_from_phi(phi)

        # Restore original mass
        psi = apply_mass_correction(xp, psi, dV_pre, M_pre)

        return psi


class PsiDirectTransport(ILevelSetTransport):
    """Direct ψ advection: advect Heaviside directly + optional reinit.

    Flow:
    1. Advect ψ directly (no logit transform)
    2. Optionally reinitialize on a fixed cadence
    """

    def __init__(
        self,
        backend: "Backend",
        advection: "ILevelSetAdvection",
        reinitializer: "IReinitializer",
        reinit_every: int = 2,
    ):
        """
        Parameters
        ----------
        backend : Backend
        advection : ILevelSetAdvection
        reinitializer : IReinitializer
        reinit_every : int
            Reinitialize every N steps (0 = never)
        """
        self.xp = backend.xp
        self.backend = backend
        self.advection = advection
        self.reinitializer = reinitializer
        self.reinit_every = int(reinit_every)

    def advance(
        self,
        psi: np.ndarray,
        velocity: List[np.ndarray],
        dt: float,
        step_index: int = 0,
    ) -> np.ndarray:
        """Direct ψ advection with optional reinit."""
        xp = self.xp

        # Advect ψ directly
        psi = xp.asarray(self.advection.advance(psi, velocity, dt))

        # Reinitialize on cadence
        if self.reinit_every > 0 and step_index % self.reinit_every == 0:
            psi = xp.asarray(self.reinitializer.reinitialize(psi))

        return psi
