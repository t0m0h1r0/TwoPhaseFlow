"""Factory helpers for initial-condition shape deserialization."""

from __future__ import annotations

from typing import Callable

from .shape_base import ShapePrimitive
from .shape_primitives import (
    Circle,
    Ellipse,
    HalfSpace,
    PerturbedCircle,
    Rectangle,
    SinusoidalInterface,
    ZalesakDisk,
)


_DEFAULT_PHASE_BY_SHAPE_TYPE = {
    "bubble": "gas",
}


def default_shape_phase(shape_type: str | None) -> str:
    """Return the default interior phase for a shape type."""
    if shape_type is None:
        return "liquid"
    return _DEFAULT_PHASE_BY_SHAPE_TYPE.get(str(shape_type), "liquid")


def _axis_index(value) -> int:
    if isinstance(value, str):
        axis = value.lower()
        if axis in {"x", "0"}:
            return 0
        if axis in {"y", "1"}:
            return 1
        raise ValueError("SinusoidalInterface: axis must be x|y|0|1.")
    return int(value)


def _wave_wavelength(data: dict) -> float:
    if "wavelength" in data:
        return float(data["wavelength"])
    mode = int(data.get("mode", 0))
    if mode <= 0:
        raise ValueError(
            "SinusoidalInterface: provide 'wavelength' or positive 'mode'."
        )
    length = float(data.get("length", data.get("domain_length", 1.0)))
    if length <= 0.0:
        raise ValueError("SinusoidalInterface: length must be positive.")
    return length / float(mode)


def _build_circle(data: dict, phase: str) -> ShapePrimitive:
    return Circle(
        center=data["center"],
        radius=data["radius"],
        interior_phase=phase,
    )


def _build_bubble(data: dict, phase: str) -> ShapePrimitive:
    return Circle(
        center=data["center"],
        radius=data["radius"],
        interior_phase=phase,
    )


def _build_rectangle(data: dict, phase: str) -> ShapePrimitive:
    if "bounds" in data:
        bounds = [tuple(bound) for bound in data["bounds"]]
    else:
        bounds = [
            (data["x_min"], data["x_max"]),
            (data["y_min"], data["y_max"]),
        ]
        if "z_min" in data:
            bounds.append((data["z_min"], data["z_max"]))
    return Rectangle(bounds=bounds, interior_phase=phase)


def _build_half_space(data: dict, phase: str) -> ShapePrimitive:
    return HalfSpace(
        normal=data["normal"],
        offset=data["offset"],
        interior_phase=phase,
    )


def _build_sinusoidal_interface(data: dict, phase: str) -> ShapePrimitive:
    return SinusoidalInterface(
        axis=_axis_index(data.get("axis", data.get("normal_axis", 1))),
        mean=float(data.get("mean", data.get("base"))),
        amplitude=float(data.get("amplitude", 0.0)),
        wavelength=_wave_wavelength(data),
        phase=float(data.get("phase", 0.0)),
        interior_phase=phase,
    )


def _build_perturbed_circle(data: dict, phase: str) -> ShapePrimitive:
    return PerturbedCircle(
        center=data["center"],
        radius=float(data["radius"]),
        epsilon=float(data.get("epsilon", 0.05)),
        mode=int(data.get("mode", 2)),
        interior_phase=phase,
    )


def _build_ellipse(data: dict, phase: str) -> ShapePrimitive:
    return Ellipse(
        center=data["center"],
        semi_axes=data["semi_axes"],
        interior_phase=phase,
    )


def _build_zalesak_disk(data: dict, phase: str) -> ShapePrimitive:
    return ZalesakDisk(
        center=data["center"],
        radius=float(data["radius"]),
        slot_width=float(data.get("slot_width", 0.025)),
        slot_depth=float(data.get("slot_depth", 0.25)),
        interior_phase=phase,
    )


_SHAPE_BUILDERS: dict[str, Callable[[dict, str], ShapePrimitive]] = {
    "bubble": _build_bubble,
    "circle": _build_circle,
    "rectangle": _build_rectangle,
    "half_space": _build_half_space,
    "sinusoidal_interface": _build_sinusoidal_interface,
    "capillary_wave": _build_sinusoidal_interface,
    "perturbed_circle": _build_perturbed_circle,
    "ellipse": _build_ellipse,
    "zalesak_disk": _build_zalesak_disk,
}


def shape_from_dict(d: dict) -> ShapePrimitive:
    """Construct a shape primitive from a plain dict."""
    data = dict(d)
    shape_type = data.pop("type", None)
    if shape_type is None:
        raise ValueError("shape dict must have a 'type' key.")

    phase = data.pop("interior_phase", default_shape_phase(shape_type))
    builder = _SHAPE_BUILDERS.get(shape_type)
    if builder is None:
        supported = "', '".join(_SHAPE_BUILDERS.keys())
        raise ValueError(
            f"Unknown shape type '{shape_type}'. "
            f"Supported: '{supported}'."
        )
    return builder(data, phase)
