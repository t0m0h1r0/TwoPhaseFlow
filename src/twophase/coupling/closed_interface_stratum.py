"""Fixed-stratum descriptors for closed-interface capillary geometry.

Symbol mapping
--------------
``K`` -> :class:`ClosedInterfaceStratum`
``q`` -> active nodal ``psi`` values restricted to one sign/cut pattern
``Gamma_h`` -> marching-squares trace on ``K``

The stratum records the discrete topology needed before differentiating
surface energy or component volume.  It is diagnostic infrastructure for the
closed-interface Riesz capillary path; it does not alter solver state.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

import numpy as np


_EDGE_CORNERS = ((0, 1), (1, 2), (2, 3), (3, 0))


@dataclass(frozen=True)
class ClosedInterfaceStratum:
    """Discrete fixed-stratum signature for a 2-D nodal interface."""

    topology_hash: str
    cell_cases: np.ndarray
    edge_crossing_count: np.ndarray
    cut_cell_count: int
    ambiguous_cell_count: int
    threshold_touch_count: int
    phase_threshold: float
    regular: bool

    def matches(self, *, xp, grid, psi, threshold_tol: float = 0.0) -> bool:
        """Return whether ``psi`` has the same fixed-stratum hash."""
        other = build_closed_interface_stratum(
            xp=xp,
            grid=grid,
            psi=psi,
            phase_threshold=self.phase_threshold,
            threshold_tol=threshold_tol,
        )
        return bool(
            self.regular
            and other.regular
            and self.topology_hash == other.topology_hash
        )


def build_closed_interface_stratum(
    *,
    xp,
    grid,
    psi,
    phase_threshold: float = 0.5,
    threshold_tol: float = 0.0,
) -> ClosedInterfaceStratum:
    """Build the fixed sign/cut pattern for a 2-D nodal ``psi`` field.

    The hash is intentionally based on topology, not coordinates.  Coordinate
    motion inside the same cut pattern is handled by geometry functionals; a
    sign-pattern change means the derivative belongs to another stratum.
    """
    if grid.ndim != 2:
        raise ValueError("ClosedInterfaceStratum currently supports 2D grids")
    psi_arr = xp.asarray(psi)
    threshold = float(phase_threshold)
    threshold_arr = xp.asarray(threshold, dtype=psi_arr.dtype)
    values = _cell_corner_values(psi_arr)
    inside = tuple(value >= threshold_arr for value in values)
    cell_cases_dev = xp.zeros_like(values[0], dtype=xp.uint8)
    for bit, mask in enumerate(inside):
        cell_cases_dev = cell_cases_dev + mask.astype(xp.uint8) * (1 << bit)

    edge_crossing_count_dev = xp.zeros_like(cell_cases_dev, dtype=xp.uint8)
    for lo, hi in _EDGE_CORNERS:
        shifted_lo = values[lo] - threshold_arr
        shifted_hi = values[hi] - threshold_arr
        edge_crossing_count_dev = edge_crossing_count_dev + (
            shifted_lo * shifted_hi < 0.0
        ).astype(xp.uint8)

    cell_cases = array_to_numpy(xp, cell_cases_dev).astype(np.uint8, copy=False)
    edge_crossing_count = array_to_numpy(
        xp,
        edge_crossing_count_dev,
    ).astype(np.uint8, copy=False)
    threshold_touch_count = int(
        array_to_numpy(
            xp,
            xp.count_nonzero(xp.abs(psi_arr - threshold_arr) <= threshold_tol),
        )
    )
    cut_cell_count = int(np.count_nonzero((cell_cases != 0) & (cell_cases != 15)))
    ambiguous_cell_count = int(np.count_nonzero((cell_cases == 5) | (cell_cases == 10)))
    regular = threshold_touch_count == 0
    return ClosedInterfaceStratum(
        topology_hash=_hash_cases(cell_cases, edge_crossing_count, threshold),
        cell_cases=cell_cases,
        edge_crossing_count=edge_crossing_count,
        cut_cell_count=cut_cell_count,
        ambiguous_cell_count=ambiguous_cell_count,
        threshold_touch_count=threshold_touch_count,
        phase_threshold=threshold,
        regular=regular,
    )


def _cell_corner_values(psi_host: np.ndarray) -> tuple[np.ndarray, ...]:
    return (
        psi_host[:-1, :-1],
        psi_host[1:, :-1],
        psi_host[1:, 1:],
        psi_host[:-1, 1:],
    )


def _hash_cases(
    cell_cases: np.ndarray,
    edge_crossing_count: np.ndarray,
    phase_threshold: float,
) -> str:
    digest = hashlib.sha256()
    digest.update(str(cell_cases.shape).encode("ascii"))
    digest.update(np.asarray(cell_cases, dtype=np.uint8).tobytes())
    digest.update(np.asarray(edge_crossing_count, dtype=np.uint8).tobytes())
    digest.update(repr(float(phase_threshold)).encode("ascii"))
    return digest.hexdigest()


def array_to_numpy(xp, array: Any) -> np.ndarray:
    """Return a host NumPy view/copy of a backend array for diagnostics."""
    if hasattr(xp, "asnumpy"):
        return np.asarray(xp.asnumpy(array))
    return np.asarray(array)
