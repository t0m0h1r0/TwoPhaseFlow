"""Face-native predictor assembly helpers for the NS step."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..core.boundary import is_all_periodic
from .face_boundary import (
    zero_wall_normal_face_components,
    zero_wall_velocity_face_components,
)


@dataclass
class FaceNativePredictorAssembly:
    """Build face-consistent predictor callbacks for pressure-robust buoyancy."""

    xp: object
    state: object
    div_op: object
    bc_type: str
    face_no_slip_boundary_state: bool
    residual_accel_builder: Callable
    coords: object = None
    Y: object = None
    ppe_coefficient_scheme: str = "phase_separated"
    face_residual_buoyancy_state: tuple | None = None

    def face_consistent_velocity_transform(self, velocity_components: list) -> None:
        """Map nodal predictor components through the carried face state."""
        if len(velocity_components) < 2:
            return
        delta_faces = self.div_op.face_fluxes(
            [
                velocity_components[0] - self.state.u,
                velocity_components[1] - self.state.v,
            ]
        )
        predictor_faces = [
            self.xp.asarray(face_velocity) + delta_face
            for face_velocity, delta_face in zip(
                self.state.face_velocity_components,
                delta_faces,
            )
        ]
        if not is_all_periodic(self.bc_type, 2):
            if self.face_no_slip_boundary_state:
                predictor_faces = zero_wall_velocity_face_components(
                    predictor_faces,
                    xp=self.xp,
                    bc_type=self.bc_type,
                )
            else:
                predictor_faces = zero_wall_normal_face_components(
                    predictor_faces,
                    xp=self.xp,
                    bc_type=self.bc_type,
                )
        mapped_components = self.div_op.reconstruct_nodes(predictor_faces)
        velocity_components[0][...] = mapped_components[0]
        velocity_components[1][...] = mapped_components[1]

    def fullband_interface_mask(self):
        """Return the one-cell-dilated active interface band."""
        if self.state.psi is None:
            return None
        psi_arr = self.xp.asarray(self.state.psi)
        band = (psi_arr > 1.0e-6) & (psi_arr < 1.0 - 1.0e-6)
        for dilation_axis in range(psi_arr.ndim):
            base_band = self.xp.copy(band)
            lower = [slice(None)] * psi_arr.ndim
            upper = [slice(None)] * psi_arr.ndim
            lower[dilation_axis] = slice(1, None)
            upper[dilation_axis] = slice(None, -1)
            band[tuple(lower)] = band[tuple(lower)] | base_band[tuple(upper)]
            band[tuple(upper)] = band[tuple(upper)] | base_band[tuple(lower)]
        return band

    def fullband_state_transform(self, velocity_components: list) -> None:
        """Use the face-consistent state only on the interface band."""
        if len(velocity_components) < 2:
            return
        raw_components = [
            self.xp.array(velocity_components[0], copy=True),
            self.xp.array(velocity_components[1], copy=True),
        ]
        self.face_consistent_velocity_transform(velocity_components)
        band = self.fullband_interface_mask()
        if band is None:
            return
        velocity_components[0][...] = self.xp.where(
            band,
            velocity_components[0],
            raw_components[0],
        )
        velocity_components[1][...] = self.xp.where(
            band,
            velocity_components[1],
            raw_components[1],
        )

    def fullband_component_transform(self, axis: int):
        """Build a transform that replaces only one component on the band."""

        def _transform(velocity_components: list) -> None:
            if len(velocity_components) < 2:
                return
            raw_components = [
                self.xp.array(velocity_components[0], copy=True),
                self.xp.array(velocity_components[1], copy=True),
            ]
            self.face_consistent_velocity_transform(velocity_components)
            band = self.fullband_interface_mask()
            if band is None:
                mapped_axis = self.xp.array(velocity_components[axis], copy=True)
            else:
                mapped_axis = self.xp.where(
                    band,
                    velocity_components[axis],
                    raw_components[axis],
                )
            velocity_components[0][...] = raw_components[0]
            velocity_components[1][...] = raw_components[1]
            velocity_components[axis][...] = mapped_axis

        return _transform

    def residual_face_buoyancy_force_builder(
        self,
        buoyancy_force_components: list,
        rho_field,
        xp_mod,
    ) -> list:
        """Build residual buoyancy force and retain its face representation."""
        residual_accel_faces = self.residual_accel_builder(
            buoyancy_force_components=buoyancy_force_components,
            rho=rho_field,
            rho_ref=self.state.rho_ref,
            g_acc=self.state.g_acc,
            div_op=self.div_op,
            xp=xp_mod,
            coords=self.coords,
            Y=self.Y,
            pressure_coefficient_scheme=self.ppe_coefficient_scheme,
        )
        if residual_accel_faces is None:
            self.face_residual_buoyancy_state = None
            return buoyancy_force_components
        residual_accel_nodes = self.div_op.reconstruct_nodes(residual_accel_faces)
        self.face_residual_buoyancy_state = (
            residual_accel_faces,
            residual_accel_nodes,
        )
        return [rho_field * residual_node for residual_node in residual_accel_nodes]
