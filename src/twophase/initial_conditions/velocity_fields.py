"""
Velocity field primitives for prescribed (externally imposed) velocity.

Each VelocityField subclass defines a velocity field u(x, t) that is imposed
on the simulation externally — bypassing the Navier-Stokes momentum equation.
Used for pure-advection benchmarks such as the Zalesak slotted-disk test.

Design mirrors shapes.py for initial conditions:
    - ABC VelocityField with compute(*coords, t=0.0) method
    - Concrete classes: RigidRotation, UniformFlow
    - Factory function velocity_field_from_dict(d) for YAML deserialization

Supported types in YAML (velocity_field.type):
    rigid_rotation   — solid-body rotation: u = -ω(y-cy), v = ω(x-cx)
    uniform          — uniform background flow: u = const, v = const
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence, Tuple

import numpy as np


# ── 基底クラス ────────────────────────────────────────────────────────────────

class VelocityField(ABC):
    """Abstract base for prescribed velocity field primitives.

    Subclasses define u(x, t) that is applied to the simulation externally.
    The field is imposed every time step via a callback, overriding the
    Navier-Stokes momentum update.
    """

    @abstractmethod
    def compute(self, *coords: np.ndarray, t: float = 0.0) -> Tuple[np.ndarray, ...]:
        """Return velocity components at the given grid coordinates.

        Parameters
        ----------
        *coords : ndarray
            Coordinate arrays (X[, Y[, Z]]) from ``grid.meshgrid()``.
        t : float
            Current simulation time (for time-dependent fields).

        Returns
        -------
        velocity : tuple of ndarray
            One array per spatial dimension (u_x, u_y[, u_z]).
            Each array has the same shape as coords[0].
        """


# ── 具象クラス ─────────────────────────────────────────────────────────────────

class RigidRotation(VelocityField):
    """Solid-body rotation velocity field (2-D).

    Velocity field::

        u = -2π (y - cy) / T
        v = +2π (x - cx) / T

    One full rotation per period T around centre (cx, cy).
    Commonly used for the Zalesak slotted-disk advection test (T = 1).

    Parameters
    ----------
    center : sequence of float
        Rotation centre (cx, cy).  Length 2 (2-D only).
    period : float
        Period of one full rotation.  Must be > 0.
    """

    def __init__(
        self,
        center: Sequence[float],
        period: float,
    ) -> None:
        if len(center) != 2:
            raise ValueError("RigidRotation: center must be a 2-element sequence (2-D only).")
        if period <= 0.0:
            raise ValueError("RigidRotation: period must be positive.")
        self.center: Tuple[float, float] = (float(center[0]), float(center[1]))
        self.period: float = float(period)

    def compute(self, *coords: np.ndarray, t: float = 0.0) -> Tuple[np.ndarray, ...]:
        """Compute (u, v) for the rigid-rotation field.

        Implements u = −2π(y − cy)/T,  v = 2π(x − cx)/T.
        """
        if len(coords) != 2:
            raise ValueError("RigidRotation.compute: only 2-D grids are supported.")
        X, Y = coords
        cx, cy = self.center
        omega = 2.0 * np.pi / self.period
        u = -omega * (Y - cy)
        v =  omega * (X - cx)
        return (u, v)


class UniformFlow(VelocityField):
    """Uniform (spatially constant) velocity field.

    Parameters
    ----------
    velocity : sequence of float
        Constant velocity components (u[, v[, w]]).
        Length must match ndim.
    """

    def __init__(self, velocity: Sequence[float]) -> None:
        self.velocity: Tuple[float, ...] = tuple(float(v) for v in velocity)

    def compute(self, *coords: np.ndarray, t: float = 0.0) -> Tuple[np.ndarray, ...]:
        """Return uniform velocity arrays matching the coordinate shapes."""
        if len(coords) != len(self.velocity):
            raise ValueError(
                f"UniformFlow.compute: expected {len(self.velocity)} coordinate arrays, "
                f"got {len(coords)}."
            )
        return tuple(np.full_like(c, v) for c, v in zip(coords, self.velocity))


# ── ファクトリ関数（YAML ディクトから生成）────────────────────────────────────

def velocity_field_from_dict(d: dict) -> VelocityField:
    """Construct a VelocityField from a plain dict (YAML deserialization).

    Parameters
    ----------
    d : dict
        Must contain a 'type' key.  Other keys depend on field type.

        rigid_rotation::

            type: rigid_rotation
            center: [0.5, 0.5]
            period: 1.0        # seconds per full revolution

        uniform::

            type: uniform
            velocity: [0.0, 1.0]  # constant (u, v)

    Returns
    -------
    field : VelocityField

    Raises
    ------
    ValueError
        Unknown field type or missing required fields.
    """
    d = dict(d)  # コピー（pop で元を壊さない）
    field_type = d.pop("type", None)
    if field_type is None:
        raise ValueError("velocity_field dict must have a 'type' key.")

    if field_type == "rigid_rotation":
        return RigidRotation(
            center=d["center"],
            period=float(d.get("period", 1.0)),
        )

    if field_type == "uniform":
        return UniformFlow(velocity=d["velocity"])

    raise ValueError(
        f"Unknown velocity_field type '{field_type}'. "
        "Supported: 'rigid_rotation', 'uniform'."
    )
