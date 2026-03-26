"""
Initial condition shape primitives.

Each shape class computes a signed distance function (SDF) φ where:
    φ < 0  inside the shape
    φ > 0  outside the shape
    φ = 0  on the boundary

Supported shapes:
    Circle      — circular (2-D) or spherical (3-D) region
    Rectangle   — axis-aligned box region (2-D or 3-D)
    HalfSpace   — half-space defined by a hyperplane n·x ≤ d

Attributes
----------
interior_phase : str
    'liquid' — inside the shape is liquid (ψ → 1 inside)
    'gas'    — inside the shape is gas   (ψ → 0 inside)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence, Tuple

import numpy as np


# ── 基底クラス ────────────────────────────────────────────────────────────────

class ShapePrimitive(ABC):
    """Abstract base for signed-distance shape primitives."""

    @property
    @abstractmethod
    def interior_phase(self) -> str:
        """'liquid' or 'gas'."""

    @abstractmethod
    def sdf(self, *coords: np.ndarray) -> np.ndarray:
        """Return signed distance field φ (negative inside).

        Parameters
        ----------
        *coords : ndarray
            Coordinate arrays (X[, Y[, Z]]) from ``numpy.meshgrid``.
            All arrays must have the same shape.

        Returns
        -------
        phi : ndarray
            Signed distance; same shape as coords[0].
        """


# ── 具象シェイプクラス ─────────────────────────────────────────────────────────

@dataclass
class Circle(ShapePrimitive):
    """Circular (2-D) or spherical (3-D) region.

    Parameters
    ----------
    center : sequence of float
        Centre coordinates (x[, y[, z]]).  Length must match ndim.
    radius : float
        Radius R > 0.
    interior_phase : str
        'liquid' (default) or 'gas'.

    SDF
    ---
    φ(x) = |x − c| − R
    """

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
        _validate_phase(interior_phase)

    @property
    def interior_phase(self) -> str:
        return self._interior_phase

    def sdf(self, *coords: np.ndarray) -> np.ndarray:
        """Signed distance from a circle/sphere boundary."""
        if len(coords) != len(self.center):
            raise ValueError(
                f"Circle.sdf: expected {len(self.center)} coordinate arrays, "
                f"got {len(coords)}"
            )
        r2 = sum(
            (c - cx) ** 2 for c, cx in zip(coords, self.center)
        )
        return np.sqrt(r2) - self.radius


@dataclass
class Rectangle(ShapePrimitive):
    """Axis-aligned rectangular (2-D) or box (3-D) region.

    Parameters
    ----------
    bounds : sequence of (lo, hi) pairs
        One ``(lo, hi)`` pair per spatial dimension.
        Example 2-D: ``[(x_min, x_max), (y_min, y_max)]``
    interior_phase : str
        'liquid' (default) or 'gas'.

    SDF
    ---
    φ(x) = max_d(lo_d − x_d, x_d − hi_d)
    Negative inside the box, zero on boundary, positive outside.
    """

    bounds: Tuple[Tuple[float, float], ...]
    _interior_phase: str = field(default="liquid", repr=False)

    def __init__(
        self,
        bounds: Sequence[Tuple[float, float]],
        interior_phase: str = "liquid",
    ) -> None:
        self.bounds = tuple(tuple(b) for b in bounds)  # type: ignore[arg-type]
        self._interior_phase = interior_phase
        _validate_phase(interior_phase)

    @property
    def interior_phase(self) -> str:
        return self._interior_phase

    def sdf(self, *coords: np.ndarray) -> np.ndarray:
        """Signed distance from an axis-aligned box boundary."""
        if len(coords) != len(self.bounds):
            raise ValueError(
                f"Rectangle.sdf: expected {len(self.bounds)} coordinate arrays, "
                f"got {len(coords)}"
            )
        # 各軸の「外側へのはみ出し」量: 正 → 外側、負 → 内側
        per_axis = [
            np.maximum(lo - c, c - hi)
            for c, (lo, hi) in zip(coords, self.bounds)
        ]
        # 全軸の最大値: 外部では最も近い面までの距離、内部では最も近い面への負の距離
        phi = per_axis[0]
        for a in per_axis[1:]:
            phi = np.maximum(phi, a)
        return phi


@dataclass
class SinusoidalInterface(ShapePrimitive):
    """Half-space bounded by a sinusoidal curve.

    The interface curve is defined as::

        coords[axis] = mean + amplitude * cos(2π * coords[perp] / wavelength)

    where ``perp = 1 - axis`` (2-D only).

    The signed distance field is::

        φ(x) = coords[axis] − (mean + amplitude * cos(2π * coords[perp] / wavelength))

    * φ < 0  ⟺  coords[axis] < interface value  (the "low" side)
    * φ > 0  ⟺  coords[axis] > interface value  (the "high" side)

    Set ``interior_phase='liquid'`` when the low side is liquid (e.g., heavy
    fluid *below* the interface in a Rayleigh–Taylor setup), or
    ``interior_phase='gas'`` for the opposite convention.

    Parameters
    ----------
    axis : int
        The axis normal to the mean interface plane (0 = x, 1 = y).
        The sinusoidal variation runs along the perpendicular axis.
    mean : float
        Mean interface position along ``axis``.
    amplitude : float
        Amplitude of the cosine perturbation.
    wavelength : float
        Wavelength of the cosine perturbation (in the perpendicular direction).
    interior_phase : str
        'liquid' (default) or 'gas' — phase of the *low* side (φ < 0).

    Examples
    --------
    Rayleigh–Taylor interface at y = 1 + 0.1·cos(2π x / 0.5),
    with heavy liquid below::

        SinusoidalInterface(axis=1, mean=1.0, amplitude=0.1,
                            wavelength=0.5, interior_phase='liquid')
    """

    axis: int
    mean: float
    amplitude: float
    wavelength: float
    _interior_phase: str = field(default="liquid", repr=False)

    def __init__(
        self,
        axis: int,
        mean: float,
        amplitude: float,
        wavelength: float,
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
        self._interior_phase = interior_phase
        _validate_phase(interior_phase)

    @property
    def interior_phase(self) -> str:
        return self._interior_phase

    def sdf(self, *coords: np.ndarray) -> np.ndarray:
        """Signed distance from the sinusoidal interface."""
        if len(coords) != 2:
            raise ValueError(
                "SinusoidalInterface.sdf: only 2-D grids are supported."
            )
        perp = 1 - self.axis
        interface = self.mean + self.amplitude * np.cos(
            2.0 * np.pi * coords[perp] / self.wavelength
        )
        return np.asarray(coords[self.axis] - interface)


@dataclass
class HalfSpace(ShapePrimitive):
    """Half-space region defined by the hyperplane n·x ≤ offset.

    The "inside" is the region where ``dot(n, x) ≤ offset``.
    The unit normal ``n`` points *outward* (away from the interior).

    Parameters
    ----------
    normal : sequence of float
        Outward unit normal vector (will be normalised internally).
    offset : float
        Signed offset d such that n·x = d defines the boundary plane.
    interior_phase : str
        'liquid' (default) or 'gas'.

    SDF
    ---
    φ(x) = n̂·x − d   (negative inside the half-space)

    Examples
    --------
    Liquid layer below y = 0.3 (outward normal points in +y direction)::

        HalfSpace(normal=(0, 1), offset=0.3, interior_phase='liquid')

    Liquid layer above y = 0.7::

        HalfSpace(normal=(0, -1), offset=-0.7, interior_phase='liquid')
    """

    normal: Tuple[float, ...]
    offset: float
    _interior_phase: str = field(default="liquid", repr=False)

    def __init__(
        self,
        normal: Sequence[float],
        offset: float,
        interior_phase: str = "liquid",
    ) -> None:
        n = np.asarray(normal, dtype=float)
        norm = float(np.linalg.norm(n))
        if norm < 1e-14:
            raise ValueError("HalfSpace: normal vector must be non-zero.")
        self.normal = tuple(n / norm)
        self.offset = float(offset)
        self._interior_phase = interior_phase
        _validate_phase(interior_phase)

    @property
    def interior_phase(self) -> str:
        return self._interior_phase

    def sdf(self, *coords: np.ndarray) -> np.ndarray:
        """Signed distance from the hyperplane; negative on the interior side."""
        if len(coords) != len(self.normal):
            raise ValueError(
                f"HalfSpace.sdf: expected {len(self.normal)} coordinate arrays, "
                f"got {len(coords)}"
            )
        # φ = n̂·x − d
        phi = sum(n * c for n, c in zip(self.normal, coords)) - self.offset
        return np.asarray(phi)


# ── ファクトリ関数（YAML ディクトから生成）────────────────────────────────────

def shape_from_dict(d: dict) -> ShapePrimitive:
    """Construct a ShapePrimitive from a plain dict (YAML deserialization).

    Parameters
    ----------
    d : dict
        Must contain a 'type' key ('circle', 'rectangle', 'half_space').
        Other keys depend on shape type (see class docs).

    Returns
    -------
    shape : ShapePrimitive

    Raises
    ------
    ValueError
        Unknown shape type or missing required fields.

    Examples
    --------
    >>> shape_from_dict({'type': 'circle', 'center': [0.5, 0.5], 'radius': 0.25})
    Circle(center=(0.5, 0.5), radius=0.25)
    >>> shape_from_dict({'type': 'rectangle',
    ...                  'bounds': [[0.0, 1.0], [0.0, 0.3]],
    ...                  'interior_phase': 'liquid'})
    Rectangle(bounds=((0.0, 1.0), (0.0, 0.3)))
    """
    d = dict(d)  # コピー（pop で元を壊さない）
    shape_type = d.pop("type", None)
    if shape_type is None:
        raise ValueError("shape dict must have a 'type' key.")

    phase = d.pop("interior_phase", "liquid")

    if shape_type == "circle":
        return Circle(
            center=d["center"],
            radius=d["radius"],
            interior_phase=phase,
        )

    if shape_type == "rectangle":
        # YAML では bounds: [[x_min, x_max], [y_min, y_max]] 形式
        if "bounds" in d:
            bounds = [tuple(b) for b in d["bounds"]]
        else:
            # 便宜上 x_min/x_max/y_min/y_max フラットキーも受け付ける (2-D のみ)
            bounds = [
                (d["x_min"], d["x_max"]),
                (d["y_min"], d["y_max"]),
            ]
            if "z_min" in d:
                bounds.append((d["z_min"], d["z_max"]))
        return Rectangle(bounds=bounds, interior_phase=phase)

    if shape_type == "half_space":
        return HalfSpace(
            normal=d["normal"],
            offset=d["offset"],
            interior_phase=phase,
        )

    if shape_type == "sinusoidal_interface":
        return SinusoidalInterface(
            axis=int(d.get("axis", 1)),
            mean=float(d["mean"]),
            amplitude=float(d.get("amplitude", 0.0)),
            wavelength=float(d["wavelength"]),
            interior_phase=phase,
        )

    raise ValueError(
        f"Unknown shape type '{shape_type}'. "
        "Supported: 'circle', 'rectangle', 'half_space', 'sinusoidal_interface'."
    )


# ── バリデーション ─────────────────────────────────────────────────────────────

def _validate_phase(phase: str) -> None:
    if phase not in ("liquid", "gas"):
        raise ValueError(
            f"interior_phase must be 'liquid' or 'gas', got '{phase}'."
        )
