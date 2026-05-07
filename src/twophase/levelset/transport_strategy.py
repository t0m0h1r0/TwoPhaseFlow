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


def _transport_projection_record(
    xp,
    *,
    triggered: bool,
    psi_before_transport,
    psi_after_transport_before_reinit,
    psi_after_reinit,
) -> dict:
    """Capture transport/reinit endpoints without changing the update."""
    record = {
        "triggered": bool(triggered),
        "psi_before_transport": xp.array(psi_before_transport, copy=True),
        "psi_after_transport_before_reinit": xp.array(
            psi_after_transport_before_reinit,
            copy=True,
        ),
        "psi_after_reinit": xp.array(psi_after_reinit, copy=True),
    }
    if triggered:
        record["psi_before"] = record["psi_after_transport_before_reinit"]
        record["psi_after"] = record["psi_after_reinit"]
    return record


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
        self.record_reinit_projection = False
        self.last_reinit_projection = {"triggered": False}

    def advance(
        self,
        psi: np.ndarray,
        velocity: List[np.ndarray],
        dt: float,
        step_index: int = 0,
    ) -> np.ndarray:
        if self.record_reinit_projection:
            self.last_reinit_projection = _transport_projection_record(
                self.xp,
                triggered=False,
                psi_before_transport=psi,
                psi_after_transport_before_reinit=psi,
                psi_after_reinit=psi,
            )
        else:
            self.last_reinit_projection = {"triggered": False}
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
        self.record_reinit_projection = False
        self.last_reinit_projection = {"triggered": False}

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
        self.last_reinit_projection = {"triggered": False}
        record_projection = bool(self.record_reinit_projection)
        psi_before_transport = xp.array(psi, copy=True) if record_projection else None
        psi_after_transport = None
        reinit_triggered = False

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
        psi_after_transport = xp.array(psi, copy=True) if record_projection else None

        # Periodic redistancing to correct interface thickness
        if step_index > 0 and (step_index % self.redist_every == 0):
            reinit_triggered = True
            psi = self.reinitializer.reinitialize(psi)
            phi = self.reconstruct.phi_from_psi(psi)
            psi = self.reconstruct.psi_from_phi(phi)

        # Restore diffuse mass unless reinit already enforced sharp volume.
        if not (
            reinit_triggered and getattr(self.reinitializer, "preserves_sharp_volume", False)
        ):
            psi = apply_mass_correction(xp, psi, dV_pre, M_pre)
        if record_projection:
            self.last_reinit_projection = _transport_projection_record(
                xp,
                triggered=reinit_triggered,
                psi_before_transport=psi_before_transport,
                psi_after_transport_before_reinit=psi_after_transport,
                psi_after_reinit=psi,
            )

        return psi

    def advance_with_face_velocity(
        self,
        psi: np.ndarray,
        face_velocity_components: List[np.ndarray],
        dt: float,
        step_index: int = 0,
    ) -> np.ndarray:
        """Phi-primary transport with projection-native face velocities."""
        self.last_reinit_projection = {"triggered": False}
        record_projection = bool(self.record_reinit_projection)
        psi_before_transport = self.xp.array(psi, copy=True) if record_projection else None
        psi_after_transport = None
        reinit_triggered = False
        advance_face = getattr(self.advection, "advance_with_face_velocity", None)
        if not callable(advance_face):
            raise RuntimeError(
                "projection-native φ transport requires "
                "advection.advance_with_face_velocity"
            )

        xp = self.xp
        dV_pre = self.grid.cell_volumes()
        M_pre = xp.sum(xp.asarray(psi) * dV_pre)

        phi = self.reconstruct.phi_from_psi(psi)
        phi = xp.asarray(
            advance_face(
                phi,
                face_velocity_components,
                dt,
                clip_bounds=None,
            )
        )
        phi = self.reconstruct.clip_phi(phi)
        psi = self.reconstruct.psi_from_phi(phi)
        psi_after_transport = xp.array(psi, copy=True) if record_projection else None

        if step_index > 0 and (step_index % self.redist_every == 0):
            reinit_triggered = True
            psi = self.reinitializer.reinitialize(psi)
            phi = self.reconstruct.phi_from_psi(psi)
            psi = self.reconstruct.psi_from_phi(phi)

        if not (
            reinit_triggered and getattr(self.reinitializer, "preserves_sharp_volume", False)
        ):
            psi = apply_mass_correction(xp, psi, dV_pre, M_pre)
        if record_projection:
            self.last_reinit_projection = _transport_projection_record(
                xp,
                triggered=reinit_triggered,
                psi_before_transport=psi_before_transport,
                psi_after_transport_before_reinit=psi_after_transport,
                psi_after_reinit=psi,
            )
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
        self.record_reinit_projection = False
        self.last_reinit_projection = {"triggered": False}
        if self.mass_correction and grid is None:
            raise ValueError("PsiDirectTransport mass correction requires grid")

    def _current_dV(self):
        """Return control volumes for the grid state current at this call."""
        if self.grid is None:
            raise ValueError("PsiDirectTransport requires grid control volumes")
        return self.grid.cell_volumes()

    def _volume_monitor(self, psi) -> float:
        monitor = getattr(self.reinitializer, "volume_monitor", None)
        if callable(monitor):
            return float(monitor(psi))
        if self.grid is None:
            raise ValueError("adaptive reinitialization requires grid or volume_monitor()")
        xp = self.xp
        dV = self._current_dV()
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
        self.last_reinit_projection = {"triggered": False}
        record_projection = bool(self.record_reinit_projection)
        psi_before_transport = xp.array(psi, copy=True) if record_projection else None
        psi_after_transport = None
        reinit_triggered = False
        if self.mass_correction:
            dV = self._current_dV()
            M_pre = xp.sum(xp.asarray(psi) * dV)

        # Advect ψ directly
        psi = xp.asarray(self.advection.advance(psi, velocity, dt))
        psi_after_transport = xp.array(psi, copy=True) if record_projection else None

        if self._should_reinitialize(psi, step_index):
            reinit_triggered = True
            psi = xp.asarray(self.reinitializer.reinitialize(psi))
            if self.reinit_trigger_mode == "adaptive":
                self._reinit_reference_monitor = max(self._volume_monitor(psi), 1.0e-30)

        if self.mass_correction and not (
            reinit_triggered and getattr(self.reinitializer, "preserves_sharp_volume", False)
        ):
            psi = apply_mass_correction(xp, psi, dV, M_pre)

        if record_projection:
            self.last_reinit_projection = _transport_projection_record(
                xp,
                triggered=reinit_triggered,
                psi_before_transport=psi_before_transport,
                psi_after_transport_before_reinit=psi_after_transport,
                psi_after_reinit=psi,
            )

        return psi

    def advance_with_face_velocity(
        self,
        psi: np.ndarray,
        face_velocity_components: List[np.ndarray],
        dt: float,
        step_index: int = 0,
    ) -> np.ndarray:
        """Direct ψ advection with projection-native face velocities."""
        self.last_reinit_projection = {"triggered": False}
        record_projection = bool(self.record_reinit_projection)
        advance_face = getattr(self.advection, "advance_with_face_velocity", None)
        if not callable(advance_face):
            raise RuntimeError(
                "projection-native ψ transport requires "
                "advection.advance_with_face_velocity"
            )

        xp = self.xp
        psi_before_transport = xp.array(psi, copy=True) if record_projection else None
        psi_after_transport = None
        reinit_triggered = False
        if self.mass_correction:
            dV = self._current_dV()
            M_pre = xp.sum(xp.asarray(psi) * dV)

        psi = xp.asarray(advance_face(psi, face_velocity_components, dt))
        psi_after_transport = xp.array(psi, copy=True) if record_projection else None

        if self._should_reinitialize(psi, step_index):
            reinit_triggered = True
            psi = xp.asarray(self.reinitializer.reinitialize(psi))
            if self.reinit_trigger_mode == "adaptive":
                self._reinit_reference_monitor = max(self._volume_monitor(psi), 1.0e-30)

        if self.mass_correction and not (
            reinit_triggered and getattr(self.reinitializer, "preserves_sharp_volume", False)
        ):
            psi = apply_mass_correction(xp, psi, dV, M_pre)

        if record_projection:
            self.last_reinit_projection = _transport_projection_record(
                xp,
                triggered=reinit_triggered,
                psi_before_transport=psi_before_transport,
                psi_after_transport_before_reinit=psi_after_transport,
                psi_after_reinit=psi,
            )

        return psi
