"""Fail-closed bridge for AO geometric q transport runtime activation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .interfaces import ILevelSetAdvection

if TYPE_CHECKING:
    from ..simulation.scheme_build_ctx import AdvectionBuildCtx


class GeometricSweptVolumeAdvectionGate(ILevelSetAdvection):
    """Register ``geometric_swept_volume`` without legacy psi fallback."""

    scheme_names = ("geometric_swept_volume",)

    @classmethod
    def _build(
        cls,
        name: str,
        ctx: "AdvectionBuildCtx",
    ) -> "GeometricSweptVolumeAdvectionGate":
        del name, ctx
        return cls()

    def advance(self, psi, velocity_components, dt, **kwargs):
        """Fail closed until solver dispatches to typed AO q transport."""
        del psi, velocity_components, dt, kwargs
        raise ValueError(
            "geometric_swept_volume must advance GeometricPhaseState.q via "
            "transport_geometric_phase_state_2d, not the legacy psi advection API"
        )
