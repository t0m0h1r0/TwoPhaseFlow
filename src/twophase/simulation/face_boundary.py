"""Face-component boundary helpers shared by NS predictor/corrector stages."""

from __future__ import annotations

from ..core.boundary import boundary_axes


def normalise_boundary_face_space(value: str | None) -> str:
    """Return the canonical direct face-space boundary convention."""
    key = str(value or "full_face").strip().lower().replace("-", "_")
    aliases = {
        "full": "full_face",
        "unconstrained": "full_face",
        "impermeable": "impermeable_face",
        "no_through": "impermeable_face",
        "normal_wall": "impermeable_face",
        "normal_wall_face": "impermeable_face",
        "free_slip": "impermeable_face",
        "slip": "impermeable_face",
        "no_slip": "constrained_face",
    }
    key = aliases.get(key, key)
    if key not in {"full_face", "impermeable_face", "constrained_face"}:
        raise ValueError(
            f"unsupported boundary_face_space={value!r}; "
            "use full_face|impermeable_face|constrained_face."
        )
    return key


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


def apply_direct_face_boundary_space(
    face_components: list,
    *,
    xp,
    bc_type: str = "wall",
    boundary_face_space: str | None = "full_face",
) -> list:
    """Project direct face components into the requested boundary face space."""
    space = normalise_boundary_face_space(boundary_face_space)
    if space == "full_face":
        return face_components
    if space == "impermeable_face":
        return zero_wall_normal_face_components(
            face_components,
            xp=xp,
            bc_type=bc_type,
        )
    return zero_wall_velocity_face_components(
        face_components,
        xp=xp,
        bc_type=bc_type,
    )
