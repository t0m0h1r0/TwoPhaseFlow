"""Common-flux conservative mass/momentum transport.

Symbol mapping:
    ``rho`` -> nodal mixture density.
    ``P`` -> nodal momentum density ``rho * u``.
    ``F_M`` -> face mass flux reconstructed from a transport ledger.
    ``K`` -> ``sum 1/2 |P|^2 / rho dV``.

The implementation consumes FCCD stage ledgers without reconstructing phase
fluxes.  All array work stays on ``backend.xp``; only callers that explicitly
inspect diagnostics should cross the host/device boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core.boundary import is_periodic_axis
from ..levelset.transport_ledger import TransportLedger


@dataclass
class ConservativeTransportResult:
    """Result and certificate for one common-flux transport step."""

    density: Any
    momentum_components: tuple[Any, ...]
    velocity_components: tuple[Any, ...]
    kinetic_energy_before: Any
    kinetic_energy_after: Any
    kinetic_energy_delta: Any
    min_density: Any
    certificate_status: str


class ConservativeCommonFluxTransport:
    """Transport ``rho`` and ``rho u`` by one recorded CLS flux ledger."""

    def __init__(self, backend, grid, fccd, *, min_density_floor: float = 1.0e-14):
        self._backend = backend
        self.xp = backend.xp
        self._grid = grid
        self._fccd = fccd
        self._min_density_floor = float(min_density_floor)
        self._dV = grid.cell_volumes()

    def advance(
        self,
        density,
        momentum_components,
        ledger: TransportLedger,
        *,
        rho_l: float,
        rho_g: float,
        fail_close: bool = True,
    ) -> ConservativeTransportResult:
        """Advance density and momentum with the same stage mass flux.

        This is the code counterpart of the common-flux theorem in
        ``CHK-RA-CH14-BUBBLE-REMEDY-001``.  Stage projections that alter
        ``psi`` without a momentum remap are rejected.
        """
        xp = self.xp
        density0 = xp.asarray(density)
        momentum0 = tuple(xp.asarray(component) for component in momentum_components)
        if len(momentum0) != self._grid.ndim:
            raise ValueError("momentum_components must have one array per grid axis")
        if ledger.mass_correction_applied:
            raise ValueError("common-flux momentum requires uncorrected flux ledger")
        if ledger.clip_bounds is not None:
            raise ValueError("common-flux momentum requires unclipped transport ledger")
        if any(stage.post_stage_projected for stage in ledger.stages):
            raise ValueError("common-flux momentum requires unprojected RK stages")

        kinetic_before = self._kinetic_energy(density0, momentum0)
        density_stage = density0
        momentum_stage = momentum0

        for stage in ledger.stages:
            mass_fluxes = self._stage_mass_fluxes(
                stage.phase_fluxes,
                ledger.face_volume_fluxes,
                rho_l=float(rho_l),
                rho_g=float(rho_g),
            )
            density_candidate = self._forward_euler_density(
                density_stage,
                mass_fluxes,
                ledger.dt,
            )
            momentum_candidate = self._forward_euler_momentum(
                density_stage,
                momentum_stage,
                mass_fluxes,
                ledger.dt,
            )
            density_stage = (
                stage.base_weight * density0
                + stage.candidate_weight * density_candidate
            )
            momentum_stage = tuple(
                stage.base_weight * p0 + stage.candidate_weight * p_candidate
                for p0, p_candidate in zip(momentum0, momentum_candidate)
            )
            min_density = xp.min(density_stage)
            if bool(self._to_host_scalar(min_density <= self._min_density_floor)):
                if fail_close:
                    raise ValueError("common-flux transport produced non-positive density")

        kinetic_after = self._kinetic_energy(density_stage, momentum_stage)
        min_density = xp.min(density_stage)
        velocity = tuple(component / density_stage for component in momentum_stage)
        status = "passed"
        if bool(self._to_host_scalar(kinetic_after > kinetic_before + 1.0e-10)):
            status = "energy_increase"
            if fail_close:
                raise ValueError("common-flux transport increased kinetic energy")

        return ConservativeTransportResult(
            density=density_stage,
            momentum_components=momentum_stage,
            velocity_components=velocity,
            kinetic_energy_before=kinetic_before,
            kinetic_energy_after=kinetic_after,
            kinetic_energy_delta=kinetic_after - kinetic_before,
            min_density=min_density,
            certificate_status=status,
        )

    def _stage_mass_fluxes(
        self,
        phase_fluxes,
        volume_fluxes,
        *,
        rho_l: float,
        rho_g: float,
    ):
        if len(phase_fluxes) != self._grid.ndim:
            raise ValueError("stage phase_fluxes must have one array per grid axis")
        if len(volume_fluxes) != self._grid.ndim:
            raise ValueError("ledger face_volume_fluxes must have one array per grid axis")
        drho = rho_l - rho_g
        return tuple(
            rho_g * self.xp.asarray(volume_flux)
            + drho * self.xp.asarray(phase_flux)
            for phase_flux, volume_flux in zip(phase_fluxes, volume_fluxes)
        )

    def _forward_euler_density(self, density, mass_fluxes, dt: float):
        divergence = self._divergence_sum(mass_fluxes)
        return density - float(dt) * divergence

    def _forward_euler_momentum(self, density, momentum_components, mass_fluxes, dt: float):
        updated = []
        for component in momentum_components:
            velocity_component = component / density
            component_fluxes = tuple(
                mass_flux * self._donor_face_value(velocity_component, mass_flux, axis)
                for axis, mass_flux in enumerate(mass_fluxes)
            )
            updated.append(component - float(dt) * self._divergence_sum(component_fluxes))
        return tuple(updated)

    def _divergence_sum(self, face_fluxes):
        xp = self.xp
        total = xp.zeros_like(self.xp.asarray(self._dV))
        for axis, face_flux in enumerate(face_fluxes):
            total = total + self._fccd.face_divergence(face_flux, axis)
        return total

    def _donor_face_value(self, nodal_value, face_flux, axis: int):
        xp = self.xp
        value_axis = xp.moveaxis(xp.asarray(nodal_value), axis, 0)
        flux_axis = xp.moveaxis(xp.asarray(face_flux), axis, 0)
        if is_periodic_axis(self._fccd.bc_type, axis, self._grid.ndim):
            n_axis = self._grid.N[axis]
            value_lo = value_axis[:n_axis]
            value_hi = xp.roll(value_lo, -1, axis=0)
        else:
            value_lo = value_axis[:-1]
            value_hi = value_axis[1:]
        donor = xp.where(flux_axis >= 0.0, value_lo, value_hi)
        return xp.moveaxis(donor, 0, axis)

    def _kinetic_energy(self, density, momentum_components):
        xp = self.xp
        momentum_sq = xp.zeros_like(density)
        for component in momentum_components:
            momentum_sq = momentum_sq + component * component
        return xp.sum(0.5 * momentum_sq / density * self._dV)

    def _to_host_scalar(self, value):
        if hasattr(value, "get"):
            value = value.get()
        if hasattr(value, "item"):
            value = value.item()
        return value
