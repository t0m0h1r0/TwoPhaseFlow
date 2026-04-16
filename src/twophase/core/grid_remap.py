"""Grid-to-grid field remapping utilities.

This module provides a small strategy hierarchy so uniform and non-uniform
grid mappings can be handled through a common interface:

    GridRemapper (base)
      ├─ IdentityGridRemapper        (source == target)
      └─ LinearGridRemapper          (separable linear interpolation)

Design notes
------------
- Uniform/non-uniform commutativity:
  The caller always uses ``GridRemapper.remap(field)``; the factory returns
  an identity mapper when coordinates match.
- GPU readiness:
  Interpolation is implemented with ``backend.xp`` primitives
  (searchsorted/take/broadcast) and runs on CPU NumPy or GPU CuPy.
- Exportability:
  ``mapping_info()`` can return source/target coordinates and optional
  precomputed interpolation weights for reproducible visualization pipelines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class RemapAxisInfo:
    """Per-axis interpolation map metadata."""

    left_index: np.ndarray
    right_index: np.ndarray
    weight_right: np.ndarray


class GridRemapper(ABC):
    """Abstract base for coordinate remappers."""

    def __init__(self, source_coords: list[np.ndarray], target_coords: list[np.ndarray]):
        self.source_coords = [np.asarray(c, dtype=float) for c in source_coords]
        self.target_coords = [np.asarray(c, dtype=float) for c in target_coords]
        if len(self.source_coords) != len(self.target_coords):
            raise ValueError("source_coords and target_coords must have the same ndim.")
        self.ndim = len(self.source_coords)

    @abstractmethod
    def remap(self, field: Any):
        """Map ``field`` from source grid nodes to target grid nodes."""

    @abstractmethod
    def mapping_info(self, include_weights: bool = False) -> dict[str, Any]:
        """Return metadata required to reproduce this mapping."""


class IdentityGridRemapper(GridRemapper):
    """No-op remapper used when source and target coordinates are identical."""

    def remap(self, field: Any):
        return field

    def mapping_info(self, include_weights: bool = False) -> dict[str, Any]:
        out = {
            "type": "identity",
            "source_coords": [c.copy() for c in self.source_coords],
            "target_coords": [c.copy() for c in self.target_coords],
        }
        if include_weights:
            out["axis"] = []
        return out


class LinearGridRemapper(GridRemapper):
    """Separable linear remapper for monotone tensor-product grids."""

    def __init__(self, backend, source_coords: list[np.ndarray], target_coords: list[np.ndarray]):
        super().__init__(source_coords, target_coords)
        self._backend = backend
        xp = backend.xp
        self._axis = []

        for ax in range(self.ndim):
            src = xp.asarray(self.source_coords[ax])
            tgt = xp.asarray(self.target_coords[ax])
            if src.ndim != 1 or tgt.ndim != 1:
                raise ValueError("Coordinates must be 1-D arrays per axis.")
            if src.size < 2:
                raise ValueError("Each source axis must have at least two nodes.")
            if bool(xp.any(src[1:] < src[:-1])):
                raise ValueError("Source coordinates must be monotone non-decreasing.")

            left = xp.searchsorted(src, tgt, side="right") - 1
            left = xp.clip(left, 0, src.size - 2)
            right = left + 1
            src_l = src[left]
            src_r = src[right]
            denom = src_r - src_l
            w_right = xp.where(xp.abs(denom) > 1e-30, (tgt - src_l) / denom, 0.0)

            self._axis.append((left, right, w_right))

    def _interp_axis(self, arr, axis: int):
        xp = self._backend.xp
        left, right, w_right = self._axis[axis]
        a0 = xp.take(arr, left, axis=axis)
        a1 = xp.take(arr, right, axis=axis)
        wshape = [1] * arr.ndim
        wshape[axis] = w_right.size
        w = w_right.reshape(tuple(wshape))
        return a0 + (a1 - a0) * w

    def remap(self, field: Any):
        xp = self._backend.xp
        out = xp.asarray(field)
        for ax in range(self.ndim):
            out = self._interp_axis(out, axis=ax)
        return out

    def mapping_info(self, include_weights: bool = False) -> dict[str, Any]:
        out: dict[str, Any] = {
            "type": "linear",
            "source_coords": [c.copy() for c in self.source_coords],
            "target_coords": [c.copy() for c in self.target_coords],
        }
        if not include_weights:
            return out

        axis_info: list[RemapAxisInfo] = []
        for left, right, w_right in self._axis:
            axis_info.append(
                RemapAxisInfo(
                    left_index=np.asarray(self._backend.to_host(left)),
                    right_index=np.asarray(self._backend.to_host(right)),
                    weight_right=np.asarray(self._backend.to_host(w_right)),
                )
            )
        out["axis"] = axis_info
        return out


def build_grid_remapper(
    backend,
    source_coords: list[np.ndarray],
    target_coords: list[np.ndarray],
    atol: float = 1e-14,
) -> GridRemapper:
    """Factory returning identity or linear remapper."""
    same = (
        len(source_coords) == len(target_coords)
        and all(
            len(a) == len(b) and np.allclose(np.asarray(a), np.asarray(b), atol=atol, rtol=0.0)
            for a, b in zip(source_coords, target_coords)
        )
    )
    if same:
        return IdentityGridRemapper(source_coords, target_coords)
    return LinearGridRemapper(backend, source_coords, target_coords)


def remap_field_to_uniform(
    backend,
    field: np.ndarray,
    source_coords: list[np.ndarray],
    domain_lengths: list[float],
    clip_range: tuple[float, float] | None = (0.0, 1.0),
) -> tuple[np.ndarray, list[np.ndarray], GridRemapper]:
    """Remap a field from non-uniform to uniform coordinates.

    Parameters
    ----------
    backend : Backend
        Compute backend (CPU or GPU).
    field : ndarray
        Field values on the non-uniform source grid.
    source_coords : list of 1-D arrays
        Per-axis node coordinates of the source grid.
    domain_lengths : list of float
        Physical domain size per axis (used to build uniform linspace targets).
    clip_range : (lo, hi) or None
        If given, clip the remapped field to ``[lo, hi]``.

    Returns
    -------
    field_uni : ndarray
        Remapped field on the uniform target grid.
    target_coords : list of 1-D arrays
        Uniform coordinate arrays for each axis.
    remapper : GridRemapper
        The remapper instance (for ``mapping_info`` export).
    """
    target_coords = [
        np.linspace(0.0, float(L), len(c))
        for c, L in zip(source_coords, domain_lengths)
    ]
    remapper = build_grid_remapper(backend, source_coords, target_coords)
    result = np.asarray(remapper.remap(field))
    if clip_range is not None:
        result = np.clip(result, clip_range[0], clip_range[1])
    return result, target_coords, remapper


def build_nonuniform_to_uniform_remapper(backend, grid, target_shape: tuple[int, ...] | None = None) -> GridRemapper:
    """Build a remapper from current grid nodes to a uniform plotting grid."""
    ndim = len(grid.coords)
    if target_shape is None:
        target_shape = tuple(len(c) for c in grid.coords)
    if len(target_shape) != ndim:
        raise ValueError("target_shape must match grid ndim.")
    target_coords = [
        np.linspace(0.0, float(grid.L[ax]), int(target_shape[ax]))
        for ax in range(ndim)
    ]
    return build_grid_remapper(backend, grid.coords, target_coords)

