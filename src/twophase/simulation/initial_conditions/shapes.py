"""Compatibility facade for initial-condition shape primitives."""

from .shape_base import ShapePrimitive, validate_shape_phase as _validate_phase
from .shape_factory import shape_from_dict
from .shape_primitives import (
    Circle,
    Ellipse,
    HalfSpace,
    Layer,
    PerturbedCircle,
    Rectangle,
    SinusoidalInterface,
    ZalesakDisk,
)

__all__ = [
    "ShapePrimitive",
    "Circle",
    "Ellipse",
    "Rectangle",
    "Layer",
    "SinusoidalInterface",
    "HalfSpace",
    "PerturbedCircle",
    "ZalesakDisk",
    "shape_from_dict",
    "_validate_phase",
]
