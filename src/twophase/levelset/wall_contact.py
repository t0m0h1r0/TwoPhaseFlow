"""No-slip wall-contact constraints for conservative level-set geometry.

Symbol mapping
--------------
``C`` / ``C(t)``:
    ``WallContactSet`` — contact-line points on a stationary solid wall.
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
class WallContactSet:
    """Collection of wall contacts for stationary no-slip walls."""

    contacts: tuple[WallContact, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.contacts)

    @classmethod
    def empty(cls) -> "WallContactSet":
        return cls(())

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

        for wall_axis in range(2):
            tangent_axis = 1 - wall_axis
            tangent_coords = coords[tangent_axis]
            for wall_side, wall_index in (("lo", 0), ("hi", -1)):
                trace = (
                    psi_h[wall_index, :]
                    if wall_axis == 0
                    else psi_h[:, wall_index]
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

        return cls(tuple(contacts))

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

    def impose_on_wall_trace(self, xp, grid, psi, *, delta: float = 0.25):
        """Impose exact linear half-level crossings at pinned contacts."""
        if not self.contacts:
            return psi
        out = xp.array(psi, copy=True)
        coords = [np.asarray(c, dtype=float) for c in grid.coords]
        delta = float(delta)

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
