"""Factory helpers for initial-condition shape deserialization."""

from __future__ import annotations

from typing import Callable

from .shape_base import ShapePrimitive
from .shape_primitives import (
    Circle,
    HalfSpace,
    PerturbedCircle,
    Rectangle,
    SinusoidalInterface,
    ZalesakDisk,
)


def _build_circle(data: dict, phase: str) -> ShapePrimitive:
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
        axis=int(data.get("axis", 1)),
        mean=float(data["mean"]),
        amplitude=float(data.get("amplitude", 0.0)),
        wavelength=float(data["wavelength"]),
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


def _build_zalesak_disk(data: dict, phase: str) -> ShapePrimitive:
    return ZalesakDisk(
        center=data["center"],
        radius=float(data["radius"]),
        slot_width=float(data.get("slot_width", 0.025)),
        slot_depth=float(data.get("slot_depth", 0.25)),
        interior_phase=phase,
    )


_SHAPE_BUILDERS: dict[str, Callable[[dict, str], ShapePrimitive]] = {
    "circle": _build_circle,
    "rectangle": _build_rectangle,
    "half_space": _build_half_space,
    "sinusoidal_interface": _build_sinusoidal_interface,
    "perturbed_circle": _build_perturbed_circle,
    "zalesak_disk": _build_zalesak_disk,
}


def shape_from_dict(d: dict) -> ShapePrimitive:
    """Construct a shape primitive from a plain dict."""
    data = dict(d)
    shape_type = data.pop("type", None)
    if shape_type is None:
        raise ValueError("shape dict must have a 'type' key.")

    phase = data.pop("interior_phase", "liquid")
    builder = _SHAPE_BUILDERS.get(shape_type)
    if builder is None:
        supported = "', '".join(_SHAPE_BUILDERS.keys())
        raise ValueError(
            f"Unknown shape type '{shape_type}'. "
            f"Supported: '{supported}'."
        )
    return builder(data, phase)
