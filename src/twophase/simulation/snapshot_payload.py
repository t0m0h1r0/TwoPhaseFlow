"""Snapshot payload helpers shared by checkpoint and runner I/O."""

from __future__ import annotations

from typing import Any

import numpy as np

PROJECTION_SNAPSHOT_FIELDS = (
    "psi_before_transport",
    "psi_after_transport_before_reinit",
    "psi_after_reinit",
)
SNAPSHOT_FIELDS = (
    "psi",
    "u",
    "v",
    "p",
    "rho",
    *PROJECTION_SNAPSHOT_FIELDS,
)


def stack_snapshot_fields(
    arrays: dict[str, np.ndarray],
    prefix: str,
    snapshots: list[dict[str, Any]],
    fields: tuple[str, ...] = SNAPSHOT_FIELDS,
) -> None:
    """Store fields present for every snapshot under ``prefix``."""
    for field in fields:
        if all(field in snap for snap in snapshots):
            arrays[f"{prefix}/{field}"] = np.stack(
                [np.asarray(snap[field]) for snap in snapshots],
                axis=0,
            )


def stack_snapshot_components(
    arrays: dict[str, np.ndarray],
    prefix: str,
    snapshots: list[dict[str, Any]],
    field: str,
) -> None:
    """Store component-valued snapshot fields as numbered arrays."""
    if not snapshots or not all(field in snap for snap in snapshots):
        return
    for axis, _component in enumerate(snapshots[0][field]):
        arrays[f"{prefix}/{field}/{axis}"] = np.stack(
            [np.asarray(snap[field][axis]) for snap in snapshots],
            axis=0,
        )


def numbered_component_series(
    arrays: dict[str, np.ndarray],
    prefix: str,
) -> list[np.ndarray]:
    """Return ``prefix/0``, ``prefix/1``... arrays in order."""
    components = []
    axis = 0
    while f"{prefix}/{axis}" in arrays:
        components.append(np.asarray(arrays[f"{prefix}/{axis}"]))
        axis += 1
    return components


def snapshot_grid_coord(coord_series, index: int, count: int) -> np.ndarray:
    """Return per-snapshot coordinates, accepting legacy single-grid files."""
    coord_series = np.asarray(coord_series)
    if coord_series.ndim >= 2 and coord_series.shape[0] == count:
        return np.asarray(coord_series[index]).copy()
    return coord_series.copy()
