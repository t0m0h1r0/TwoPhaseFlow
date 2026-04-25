"""Concrete initial-condition shape primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence, Tuple

import numpy as np

from .shape_base import ShapePrimitive, validate_shape_phase


def _xp_like(array):
    if type(array).__module__.split(".", 1)[0] == "cupy":
        import cupy as cp
        return cp
    return np


@dataclass
class Circle(ShapePrimitive):
    center: Tuple[float, ...]
    radius: float
    _interior_phase: str = field(default="liquid", repr=False)

    def __init__(
        self,
        center: Sequence[float],
        radius: float,
        interior_phase: str = "liquid",
    ) -> None:
        self.center = tuple(center)
        self.radius = radius
        self._interior_phase = interior_phase
        validate_shape_phase(interior_phase)

    @property
    def interior_phase(self) -> str:
        return self._interior_phase

    def sdf(self, *coords: np.ndarray) -> np.ndarray:
        if len(coords) != len(self.center):
            raise ValueError(
                f"Circle.sdf: expected {len(self.center)} coordinate arrays, "
                f"got {len(coords)}"
            )
        r2 = sum((c - cx) ** 2 for c, cx in zip(coords, self.center))
        return np.sqrt(r2) - self.radius


@dataclass
class Rectangle(ShapePrimitive):
    bounds: Tuple[Tuple[float, float], ...]
    _interior_phase: str = field(default="liquid", repr=False)

    def __init__(
        self,
        bounds: Sequence[Tuple[float, float]],
        interior_phase: str = "liquid",
    ) -> None:
        self.bounds = tuple(tuple(b) for b in bounds)  # type: ignore[arg-type]
        self._interior_phase = interior_phase
        validate_shape_phase(interior_phase)

    @property
    def interior_phase(self) -> str:
        return self._interior_phase

    def sdf(self, *coords: np.ndarray) -> np.ndarray:
        if len(coords) != len(self.bounds):
            raise ValueError(
                f"Rectangle.sdf: expected {len(self.bounds)} coordinate arrays, "
                f"got {len(coords)}"
            )
        per_axis = [
            np.maximum(lo - c, c - hi)
            for c, (lo, hi) in zip(coords, self.bounds)
        ]
        phi = per_axis[0]
        for axis_phi in per_axis[1:]:
            phi = np.maximum(phi, axis_phi)
        return phi


@dataclass
class SinusoidalInterface(ShapePrimitive):
    axis: int
    mean: float
    amplitude: float
    wavelength: float
    phase: float
    _interior_phase: str = field(default="liquid", repr=False)

    def __init__(
        self,
        axis: int,
        mean: float,
        amplitude: float,
        wavelength: float,
        phase: float = 0.0,
        interior_phase: str = "liquid",
    ) -> None:
        if axis not in (0, 1):
            raise ValueError("SinusoidalInterface: axis must be 0 or 1 (2-D only).")
        if wavelength <= 0:
            raise ValueError("SinusoidalInterface: wavelength must be positive.")
        self.axis = axis
        self.mean = float(mean)
        self.amplitude = float(amplitude)
        self.wavelength = float(wavelength)
        self.phase = float(phase)
        self._interior_phase = interior_phase
        validate_shape_phase(interior_phase)

    @property
    def interior_phase(self) -> str:
        return self._interior_phase

    def sdf(self, *coords: np.ndarray) -> np.ndarray:
        if len(coords) != 2:
            raise ValueError(
                "SinusoidalInterface.sdf: only 2-D grids are supported."
        )
        perp = 1 - self.axis
        xp = _xp_like(coords[perp])
        interface = self.mean + self.amplitude * xp.cos(
            2.0 * np.pi * coords[perp] / self.wavelength + self.phase
        )
        return coords[self.axis] - interface


@dataclass
class HalfSpace(ShapePrimitive):
    normal: Tuple[float, ...]
    offset: float
    _interior_phase: str = field(default="liquid", repr=False)

    def __init__(
        self,
        normal: Sequence[float],
        offset: float,
        interior_phase: str = "liquid",
    ) -> None:
        normal_array = np.asarray(normal, dtype=float)
        norm = float(np.linalg.norm(normal_array))
        if norm < 1e-14:
            raise ValueError("HalfSpace: normal vector must be non-zero.")
        self.normal = tuple(normal_array / norm)
        self.offset = float(offset)
        self._interior_phase = interior_phase
        validate_shape_phase(interior_phase)

    @property
    def interior_phase(self) -> str:
        return self._interior_phase

    def sdf(self, *coords: np.ndarray) -> np.ndarray:
        if len(coords) != len(self.normal):
            raise ValueError(
                f"HalfSpace.sdf: expected {len(self.normal)} coordinate arrays, "
                f"got {len(coords)}"
            )
        phi = sum(n * c for n, c in zip(self.normal, coords)) - self.offset
        return np.asarray(phi)


@dataclass
class PerturbedCircle(ShapePrimitive):
    center: tuple
    radius: float
    epsilon: float
    mode: int
    _interior_phase: str = field(default="liquid", repr=False)

    def __init__(
        self,
        center,
        radius: float,
        epsilon: float = 0.05,
        mode: int = 2,
        interior_phase: str = "liquid",
    ) -> None:
        self.center = tuple(center)
        self.radius = float(radius)
        self.epsilon = float(epsilon)
        self.mode = int(mode)
        self._interior_phase = interior_phase
        validate_shape_phase(interior_phase)

    @property
    def interior_phase(self) -> str:
        return self._interior_phase

    def sdf(self, *coords: np.ndarray) -> np.ndarray:
        if len(coords) != 2:
            raise ValueError("PerturbedCircle.sdf: only 2-D grids supported.")
        X, Y = coords
        cx, cy = self.center
        dx = X - cx
        dy = Y - cy
        r = np.sqrt(dx ** 2 + dy ** 2)
        theta = np.arctan2(dy, dx)
        r_boundary = self.radius * (1.0 + self.epsilon * np.cos(self.mode * theta))
        return r - r_boundary


@dataclass
class ZalesakDisk(ShapePrimitive):
    center: Tuple[float, float]
    radius: float
    slot_width: float
    slot_depth: float
    _interior_phase: str = field(default="liquid", repr=False)

    def __init__(
        self,
        center: Sequence[float],
        radius: float,
        slot_width: float = 0.05,
        slot_depth: float = 0.25,
        interior_phase: str = "liquid",
    ) -> None:
        if len(center) != 2:
            raise ValueError("ZalesakDisk: center must be 2-D.")
        self.center = (float(center[0]), float(center[1]))
        self.radius = float(radius)
        self.slot_width = float(slot_width)
        self.slot_depth = float(slot_depth)
        self._interior_phase = interior_phase
        validate_shape_phase(interior_phase)

    @property
    def interior_phase(self) -> str:
        return self._interior_phase

    def sdf(self, *coords: np.ndarray) -> np.ndarray:
        if len(coords) != 2:
            raise ValueError("ZalesakDisk.sdf: only 2-D grids are supported.")
        X, Y = coords
        cx, cy = self.center
        R, w, d = self.radius, self.slot_width, self.slot_depth
        phi_circle = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) - R
        slot_x_min = cx - w / 2.0
        slot_x_max = cx + w / 2.0
        slot_y_max = cy - R + d
        dx = np.maximum(slot_x_min - X, X - slot_x_max)
        dy = np.maximum(-1e10 - Y, Y - slot_y_max)
        phi_slot = np.maximum(dx, dy)
        return np.maximum(phi_circle, -phi_slot)
