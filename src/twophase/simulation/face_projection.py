"""Shared face-flux projection helpers for divergence operators."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.boundary import is_periodic_axis, sync_periodic_image_nodes

if TYPE_CHECKING:
    from ..core.grid import Grid


def axis_slice(ndim: int, axis: int, start: int, stop: int) -> tuple[slice, ...]:
    """Return an axis-aligned slice for node/face arrays."""
    slices = [slice(None)] * ndim
    slices[axis] = slice(start, stop)
    return tuple(slices)


def reconstruct_nodes_from_faces(
    xp,
    grid: "Grid",
    face_components: list,
    bc_type: str = "wall",
) -> list:
    """Reconstruct nodal components from normal face fluxes on ``grid``."""
    nodal_components = []
    ndim = grid.ndim
    for axis, face_component in enumerate(face_components):
        n_cells = grid.N[axis]
        nodal_component = xp.zeros(grid.shape, dtype=face_component.dtype)
        if is_periodic_axis(bc_type, axis, ndim):
            nodal_component[axis_slice(ndim, axis, 0, n_cells)] = 0.5 * (
                face_component
                + xp.roll(face_component, shift=1, axis=axis)
            )
            nodal_component[axis_slice(ndim, axis, n_cells, n_cells + 1)] = (
                nodal_component[axis_slice(ndim, axis, 0, 1)]
            )
        else:
            nodal_component[axis_slice(ndim, axis, 1, n_cells)] = 0.5 * (
                face_component[axis_slice(ndim, axis, 0, n_cells - 1)]
                + face_component[axis_slice(ndim, axis, 1, n_cells)]
            )
            nodal_component[axis_slice(ndim, axis, 0, 1)] = face_component[
                axis_slice(ndim, axis, 0, 1)
            ]
            nodal_component[axis_slice(ndim, axis, n_cells, n_cells + 1)] = (
                face_component[axis_slice(ndim, axis, n_cells - 1, n_cells)]
            )
        sync_periodic_image_nodes(nodal_component, bc_type)
        nodal_components.append(nodal_component)
    return nodal_components


def zero_face_components(xp, face_components: list) -> list:
    """Return zero force terms with shapes matching ``face_components``."""
    return [xp.zeros_like(face_component) for face_component in face_components]


def apply_pressure_projection(
    face_components: list,
    pressure_faces: list,
    force_faces: list,
    dt: float,
) -> list:
    """Apply ``u_f - dt * p_f + dt * f_f`` componentwise on face arrays."""
    return [
        face_component - dt * pressure_face + dt * force_face
        for face_component, pressure_face, force_face in zip(
            face_components, pressure_faces, force_faces
        )
    ]
