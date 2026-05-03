"""Level-set transport strategy (advection + reinit + redistancing).

Encapsulates two distinct paths:
1. PhiPrimaryTransport — logit-space advection (φ) + mass correction
2. PsiDirectTransport — direct ψ advection + mass correction + optional reinit

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
    """Direct ψ advection: advect Heaviside directly + mass correction + optional reinit.

    Flow:
    1. Advect ψ directly (no logit transform)
    2. Optionally reinitialize on a fixed cadence
    3. Apply interface-weighted mass correction in ψ-space
    """

    def __init__(
        self,
        backend: "Backend",
        advection: "ILevelSetAdvection",
        reinitializer: "IReinitializer",
        reinit_every: int = 2,
        grid=None,
        mass_correction: bool = False,
        reinit_trigger_mode: str = "fixed",
        reinit_threshold: float = 1.10,
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
        self.grid = grid
        self.mass_correction = bool(mass_correction)
        self.reinit_trigger_mode = str(reinit_trigger_mode).strip().lower()
        if self.reinit_trigger_mode not in {"fixed", "adaptive"}:
            raise ValueError(
                "reinit_trigger_mode must be 'adaptive' or 'fixed', "
                f"got {reinit_trigger_mode!r}"
            )
        self.reinit_threshold = float(reinit_threshold)
        if self.reinit_threshold <= 1.0:
            raise ValueError("reinit_threshold must be > 1.0")
        self._reinit_reference_monitor: float | None = None
        if self.mass_correction and grid is None:
            raise ValueError("PsiDirectTransport mass correction requires grid")
        self._dV = grid.cell_volumes() if self.mass_correction else None

    def _volume_monitor(self, psi) -> float:
        monitor = getattr(self.reinitializer, "volume_monitor", None)
        if callable(monitor):
            return float(monitor(psi))
        if self.grid is None:
            raise ValueError("adaptive reinitialization requires grid or volume_monitor()")
        xp = self.xp
        dV = self._dV if self._dV is not None else self.grid.cell_volumes()
        value = xp.sum(xp.asarray(psi) * (1.0 - xp.asarray(psi)) * dV)
        return self.backend.to_scalar(value)

    def _should_reinitialize(self, psi, step_index: int) -> bool:
        if self.reinit_trigger_mode == "adaptive":
            monitor = self._volume_monitor(psi)
            if self._reinit_reference_monitor is None:
                self._reinit_reference_monitor = max(monitor, 1.0e-30)
                return False
            ratio = monitor / max(self._reinit_reference_monitor, 1.0e-30)
            return ratio > self.reinit_threshold
        return self.reinit_every > 0 and step_index > 0 and step_index % self.reinit_every == 0

    def advance(
        self,
        psi: np.ndarray,
        velocity: List[np.ndarray],
        dt: float,
        step_index: int = 0,
    ) -> np.ndarray:
        """Direct ψ advection with optional reinit."""
        xp = self.xp
        if self.mass_correction:
            M_pre = xp.sum(xp.asarray(psi) * self._dV)

        # Advect ψ directly
        psi = xp.asarray(self.advection.advance(psi, velocity, dt))

        if self._should_reinitialize(psi, step_index):
            psi = xp.asarray(self.reinitializer.reinitialize(psi))
            if self.reinit_trigger_mode == "adaptive":
                self._reinit_reference_monitor = max(self._volume_monitor(psi), 1.0e-30)

        if self.mass_correction:
            psi = apply_mass_correction(xp, psi, self._dV, M_pre)

        return psi

    def advance_with_face_velocity(
        self,
        psi: np.ndarray,
        face_velocity_components: List[np.ndarray],
        dt: float,
        step_index: int = 0,
    ) -> np.ndarray:
        """Direct ψ advection with projection-native face velocities."""
        advance_face = getattr(self.advection, "advance_with_face_velocity", None)
        if not callable(advance_face):
            raise RuntimeError(
                "projection-native ψ transport requires "
                "advection.advance_with_face_velocity"
            )

        xp = self.xp
        if self.mass_correction:
            M_pre = xp.sum(xp.asarray(psi) * self._dV)

        psi = xp.asarray(advance_face(psi, face_velocity_components, dt))

        if self._should_reinitialize(psi, step_index):
            psi = xp.asarray(self.reinitializer.reinitialize(psi))
            if self.reinit_trigger_mode == "adaptive":
                self._reinit_reference_monitor = max(self._volume_monitor(psi), 1.0e-30)

        if self.mass_correction:
            psi = apply_mass_correction(xp, psi, self._dV, M_pre)

        return psi
