"""Face-component boundary helpers shared by NS predictor/corrector stages."""

from __future__ import annotations

from ..core.boundary import boundary_axes


def zero_wall_normal_face_components(
    face_components: list,
    *,
    xp,
    bc_type: str = "wall",
) -> list:
    """Return face components with wall-normal boundary fluxes set to zero."""
    bounded = []
    ndim = face_components[0].ndim
    axes = boundary_axes(bc_type, ndim)
    for axis, face in enumerate(face_components):
        bounded_face = xp.array(face, copy=True)
        if axes[axis] != "wall":
            bounded.append(bounded_face)
            continue
        lower = [slice(None)] * ndim
        upper = [slice(None)] * ndim
        lower[axis] = 0
        upper[axis] = -1
        bounded_face[tuple(lower)] = 0.0
        bounded_face[tuple(upper)] = 0.0
        bounded.append(bounded_face)
    return bounded


def zero_wall_velocity_face_components(
    face_components: list,
    *,
    xp,
    bc_type: str = "wall",
) -> list:
    """Return face-velocity components with no-slip wall faces set to zero."""
    bounded = []
    axes = boundary_axes(bc_type, face_components[0].ndim)
    for face in face_components:
        bounded_face = xp.array(face, copy=True)
        for axis in range(bounded_face.ndim):
            if axes[axis] != "wall":
                continue
            lower = [slice(None)] * bounded_face.ndim
            upper = [slice(None)] * bounded_face.ndim
            lower[axis] = 0
            upper[axis] = -1
            bounded_face[tuple(lower)] = 0.0
            bounded_face[tuple(upper)] = 0.0
        bounded.append(bounded_face)
    return bounded
