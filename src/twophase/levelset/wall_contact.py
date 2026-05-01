"""No-slip wall-contact constraints for conservative level-set geometry.

Symbol mapping
--------------
``C`` / ``C(t)``:
    ``WallContactSet`` — contact-line points on a stationary solid wall.
``sign(psi_w - 1/2)``:
    ``WallTrace`` — material phase side restricted to a stationary wall.
``s``:
    ``coordinate`` — physical tangent coordinate along a wall.
``X_w(s)``:
    ``physical_point`` — physical point obtained from wall side and tangent
    coordinate.
``chi_free``:
    ``free_mask`` — nodes allowed to receive global mass correction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

import numpy as np


WallSide = Literal["lo", "hi"]
ContactMode = Literal["pinned_no_slip"]
AngleMode = Literal["initial", "mirror_neutral", "unspecified"]


@dataclass(frozen=True)
class WallContact:
    """A pinned no-slip contact point stored in physical coordinates."""

    wall_axis: int
    wall_side: WallSide
    tangent_axis: int
    coordinate: float
    orientation: float
    mode: ContactMode = "pinned_no_slip"
    angle_mode: AngleMode = "mirror_neutral"
    level: float = 0.5

    def wall_coordinate(self, grid) -> float:
        """Return the fixed coordinate normal to the wall."""
        return 0.0 if self.wall_side == "lo" else float(grid.L[self.wall_axis])

    def physical_point(self, grid) -> tuple[float, float]:
        """Return the 2-D physical point represented by this contact."""
        point = [0.0, 0.0]
        point[self.wall_axis] = self.wall_coordinate(grid)
        point[self.tangent_axis] = self.coordinate
        return float(point[0]), float(point[1])


@dataclass(frozen=True)
class WallTrace:
    """Initial no-slip wall phase side stored in physical coordinates.

    A3 chain:
        Equation: ``D psi / Dt = 0`` with ``u|wall = 0``.
        Sharp-interface result: wall phase intervals and contact roots are
        invariant unless a slip/contact-line law is introduced.
        Discretization: store the initial sign of ``psi_w - 1/2`` and project
        only boundary nodes that would create new wall contacts.
    """

    wall_axis: int
    wall_side: WallSide
    tangent_axis: int
    tangent_coordinates: tuple[float, ...]
    values: tuple[float, ...]
    level: float = 0.5

    def wall_index(self) -> int:
        """Return the boundary index associated with this wall side."""
        return 0 if self.wall_side == "lo" else -1

    def sample(self, tangent_coordinates: np.ndarray) -> np.ndarray:
        """Interpolate the initial trace onto current wall coordinates."""
        source_coordinates = np.asarray(self.tangent_coordinates, dtype=float)
        source_values = np.asarray(self.values, dtype=float)
        current_coordinates = np.asarray(tangent_coordinates, dtype=float)
        sampled = np.interp(
            current_coordinates,
            source_coordinates,
            source_values,
            left=source_values[0],
            right=source_values[-1],
        )
        return np.clip(sampled, 0.0, 1.0)

    def phase_side(self, tangent_coordinates: np.ndarray) -> np.ndarray:
        """Return the initial wall phase side at current coordinates."""
        return np.sign(self.sample(tangent_coordinates) - self.level)


@dataclass(frozen=True)
class WallContactSet:
    """Wall geometry constraints for stationary no-slip boundaries."""

    contacts: tuple[WallContact, ...] = ()
    traces: tuple[WallTrace, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.contacts or self.traces)

    @classmethod
    def empty(cls) -> "WallContactSet":
        return cls((), ())

    @classmethod
    def detect_from_psi(
        cls,
        psi,
        grid,
        *,
        bc_type: str = "wall",
        level: float = 0.5,
    ) -> "WallContactSet":
        """Detect initial wall contacts from the wall trace of ``psi``.

        The detector records physical contact coordinates only for stationary
        wall boundaries.  Periodic or non-wall configurations intentionally
        return an empty set.
        """
        if bc_type != "wall" or grid.ndim != 2:
            return cls.empty()

        psi_h = np.asarray(psi, dtype=float)
        coords = [np.asarray(c, dtype=float) for c in grid.coords]
        contacts: list[WallContact] = []
        traces: list[WallTrace] = []

        for wall_axis in range(2):
            tangent_axis = 1 - wall_axis
            tangent_coords = coords[tangent_axis]
            for wall_side, wall_index in (("lo", 0), ("hi", -1)):
                trace = (
                    psi_h[wall_index, :]
                    if wall_axis == 0
                    else psi_h[:, wall_index]
                )
                traces.append(
                    WallTrace(
                        wall_axis=wall_axis,
                        wall_side=wall_side,
                        tangent_axis=tangent_axis,
                        tangent_coordinates=tuple(float(v) for v in tangent_coords),
                        values=tuple(float(v) for v in trace),
                        level=float(level),
                    )
                )
                contacts.extend(
                    _contacts_on_trace(
                        trace,
                        tangent_coords,
                        wall_axis=wall_axis,
                        wall_side=wall_side,
                        tangent_axis=tangent_axis,
                        level=level,
                    )
                )

        return cls(tuple(contacts), tuple(traces))

    def physical_points(self, grid) -> tuple[tuple[float, float], ...]:
        """Return pinned contacts as ``(x, y)`` physical points."""
        return tuple(contact.physical_point(grid) for contact in self.contacts)

    def projected_coordinates(self, axis: int, grid) -> np.ndarray:
        """Return pinned-contact projections onto one physical axis."""
        values: list[float] = []
        for contact in self.contacts:
            if axis == contact.wall_axis:
                values.append(contact.wall_coordinate(grid))
            elif axis == contact.tangent_axis:
                values.append(contact.coordinate)
        return np.asarray(values, dtype=float)

    def nearest_node_seeds(self, grid) -> list[tuple[int, int, float]]:
        """Return nearest-node FMM zero seeds for pinned contacts."""
        coords = [np.asarray(c, dtype=float) for c in grid.coords]
        seeds: list[tuple[int, int, float]] = []
        for contact in self.contacts:
            index = [0, 0]
            index[contact.wall_axis] = (
                0 if contact.wall_side == "lo" else len(coords[contact.wall_axis]) - 1
            )
            tangent = coords[contact.tangent_axis]
            index[contact.tangent_axis] = int(np.argmin(np.abs(tangent - contact.coordinate)))
            seeds.append((int(index[0]), int(index[1]), 0.0))
        return seeds

    def contact_mask(
        self,
        xp,
        grid,
        shape: tuple[int, int],
        *,
        band_width: float | None = None,
        normal_layers: int = 2,
    ):
        """Return mask of nodes excluded from global mass correction."""
        mask = xp.zeros(shape, dtype=bool)
        if not self.contacts:
            return mask
        if band_width is None:
            band_width = 2.0 * _h_min(grid)

        coords = [xp.asarray(c) for c in grid.coords]
        layers = max(1, int(normal_layers))
        for contact in self.contacts:
            tangent = coords[contact.tangent_axis]
            tangent_mask = xp.abs(tangent - contact.coordinate) <= band_width
            if contact.wall_axis == 0:
                normal_slice = slice(0, layers) if contact.wall_side == "lo" else slice(-layers, None)
                mask[normal_slice, :] = mask[normal_slice, :] | tangent_mask.reshape(1, -1)
            else:
                normal_slice = slice(0, layers) if contact.wall_side == "lo" else slice(-layers, None)
                mask[:, normal_slice] = mask[:, normal_slice] | tangent_mask.reshape(-1, 1)
        return mask

    def wall_trace_mask(
        self,
        xp,
        shape: tuple[int, int],
        *,
        normal_layers: int = 1,
    ):
        """Return mask of full wall-trace nodes constrained by no-slip."""
        mask = xp.zeros(shape, dtype=bool)
        if not self.traces:
            return mask
        layers = max(1, int(normal_layers))
        for trace in self.traces:
            if trace.wall_axis == 0:
                normal_slice = slice(0, layers) if trace.wall_side == "lo" else slice(-layers, None)
                mask[normal_slice, :] = True
            else:
                normal_slice = slice(0, layers) if trace.wall_side == "lo" else slice(-layers, None)
                mask[:, normal_slice] = True
        return mask

    def constraint_mask(
        self,
        xp,
        grid,
        shape: tuple[int, int],
        *,
        band_width: float | None = None,
        contact_layers: int = 1,
    ):
        """Return contact-root nodes excluded from mass correction."""
        contact_nodes = self.contact_mask(
            xp,
            grid,
            shape,
            band_width=band_width,
            normal_layers=contact_layers,
        )
        return contact_nodes

    def impose_on_wall_trace(self, xp, grid, psi, *, delta: float = 0.25):
        """Project wall phase topology and exact contacts onto no-slip data."""
        if not self:
            return psi
        out = xp.array(psi, copy=True)
        coords = [np.asarray(c, dtype=float) for c in grid.coords]
        delta = float(delta)

        for trace in self.traces:
            tangent = coords[trace.tangent_axis]
            phase_side = trace.phase_side(tangent)
            wall_index = trace.wall_index()
            level = float(trace.level)
            low_value = np.nextafter(level, 0.0)
            high_value = np.nextafter(level, 1.0)
            if trace.wall_axis == 0:
                wall_values = out[wall_index, :]
                high_mask = xp.asarray(phase_side > 0.0)
                low_mask = xp.asarray(phase_side < 0.0)
                out[wall_index, :] = xp.where(
                    high_mask & (wall_values <= level),
                    high_value,
                    xp.where(low_mask & (wall_values >= level), low_value, wall_values),
                )
            else:
                wall_values = out[:, wall_index]
                high_mask = xp.asarray(phase_side > 0.0)
                low_mask = xp.asarray(phase_side < 0.0)
                out[:, wall_index] = xp.where(
                    high_mask & (wall_values <= level),
                    high_value,
                    xp.where(low_mask & (wall_values >= level), low_value, wall_values),
                )

        for contact in self.contacts:
            tangent = coords[contact.tangent_axis]
            if contact.coordinate <= tangent[0]:
                left = 0
                frac = 0.0
            elif contact.coordinate >= tangent[-1]:
                left = len(tangent) - 2
                frac = 1.0
            else:
                left = int(np.searchsorted(tangent, contact.coordinate, side="right") - 1)
                left = min(max(left, 0), len(tangent) - 2)
                width = tangent[left + 1] - tangent[left]
                frac = 0.0 if width == 0.0 else (contact.coordinate - tangent[left]) / width

            orient = 1.0 if contact.orientation >= 0.0 else -1.0
            lo_value = contact.level - orient * delta * frac
            hi_value = contact.level + orient * delta * (1.0 - frac)
            wall_index = 0 if contact.wall_side == "lo" else -1

            if contact.wall_axis == 0:
                out[wall_index, left] = lo_value
                out[wall_index, left + 1] = hi_value
            else:
                out[left, wall_index] = lo_value
                out[left + 1, wall_index] = hi_value

        return xp.clip(out, 0.0, 1.0)


def apply_masked_mass_correction(xp, q, dV, target_mass, free_mask):
    """Apply interface-weighted mass correction only on ``free_mask`` nodes."""
    q_dev = xp.asarray(q)
    w = 4.0 * q_dev * (1.0 - q_dev) * xp.asarray(free_mask, dtype=q_dev.dtype)
    current_mass = xp.sum(q_dev * dV)
    weight = xp.sum(w * dV)
    weight_safe = xp.where(weight > 1e-12, weight, 1.0)
    gate = xp.where(weight > 1e-12, 1.0, 0.0)
    ratio = (xp.asarray(target_mass) - current_mass) / weight_safe
    return xp.clip(q_dev + gate * ratio * w, 0.0, 1.0)


def _contacts_on_trace(
    trace: np.ndarray,
    tangent_coords: np.ndarray,
    *,
    wall_axis: int,
    wall_side: WallSide,
    tangent_axis: int,
    level: float,
) -> Iterable[WallContact]:
    shifted = np.asarray(trace, dtype=float) - level
    contacts: list[WallContact] = []
    for index in range(len(tangent_coords) - 1):
        left = shifted[index]
        right = shifted[index + 1]
        if left == 0.0:
            coordinate = tangent_coords[index]
        elif right == 0.0:
            coordinate = tangent_coords[index + 1]
        elif left * right < 0.0:
            denom = abs(left) + abs(right)
            frac = abs(left) / denom if denom > 0.0 else 0.0
            coordinate = tangent_coords[index] + frac * (tangent_coords[index + 1] - tangent_coords[index])
        else:
            continue
        orientation = np.sign(right - left)
        if orientation == 0.0:
            orientation = 1.0
        contacts.append(
            WallContact(
                wall_axis=wall_axis,
                wall_side=wall_side,
                tangent_axis=tangent_axis,
                coordinate=float(coordinate),
                orientation=float(orientation),
                level=float(level),
            )
        )
    return contacts


def _h_min(grid) -> float:
    return float(min(np.min(grid.h[axis]) for axis in range(grid.ndim)))
