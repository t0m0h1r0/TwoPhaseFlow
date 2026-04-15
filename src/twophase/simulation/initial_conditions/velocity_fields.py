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


def _xp_of(arr):
    """Return the array module (numpy or cupy) that owns *arr*."""
    try:
        import cupy
        return cupy.get_array_module(arr)
    except (ImportError, AttributeError):
        return np


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
        xp = _xp_of(coords[0])
        X, Y = coords
        cx, cy = self.center
        omega = 2.0 * xp.pi / self.period
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
        xp = _xp_of(coords[0])
        return tuple(xp.full_like(c, v) for c, v in zip(coords, self.velocity))


class SingleVortex(VelocityField):
    """Time-reversible single-vortex deformation field (LeVeque 1996).

    Velocity field::

        u = -sin(pi*x)^2 * sin(2*pi*y) * cos(pi*t/T)
        v =  sin(pi*y)^2 * sin(2*pi*x) * cos(pi*t/T)

    The field reverses at t = T/2 and returns the interface to its
    initial shape at t = T, providing a quantitative advection error metric.

    Parameters
    ----------
    period : float
        Reversal period T (default 1.0).
    """

    def __init__(self, period: float = 1.0) -> None:
        if period <= 0.0:
            raise ValueError("SingleVortex: period must be positive.")
        self.period = float(period)

    def compute(self, *coords: np.ndarray, t: float = 0.0) -> Tuple[np.ndarray, ...]:
        if len(coords) != 2:
            raise ValueError("SingleVortex.compute: only 2-D grids are supported.")
        xp = _xp_of(coords[0])
        X, Y = coords
        T = self.period
        cos_t = float(xp.cos(xp.asarray(np.pi * t / T)))
        u = -(xp.sin(np.pi * X) ** 2) * xp.sin(2.0 * np.pi * Y) * cos_t
        v =  (xp.sin(np.pi * Y) ** 2) * xp.sin(2.0 * np.pi * X) * cos_t
        return (u, v)


class DoubleShearLayer(VelocityField):
    """Double shear layer velocity field (2-D).

    Velocity field on domain [0, 2*pi]^2::

        u = tanh((y - pi/2) / delta)   for y <= pi
            tanh((3*pi/2 - y) / delta)  for y > pi
        v = eps * sin(x)

    Standard benchmark for inviscid Kelvin-Helmholtz instability.

    Parameters
    ----------
    delta : float
        Shear layer thickness parameter (default 0.05).
    eps : float
        Perturbation amplitude (default 0.05).
    """

    def __init__(self, delta: float = 0.05, eps: float = 0.05) -> None:
        self.delta = float(delta)
        self.eps = float(eps)

    def compute(self, *coords: np.ndarray, t: float = 0.0) -> Tuple[np.ndarray, ...]:
        if len(coords) != 2:
            raise ValueError("DoubleShearLayer.compute: only 2-D grids are supported.")
        xp = _xp_of(coords[0])
        X, Y = coords
        d = self.delta
        u = xp.where(
            Y <= np.pi,
            xp.tanh((Y - np.pi / 2.0) / d),
            xp.tanh((3.0 * np.pi / 2.0 - Y) / d),
        )
        v = self.eps * xp.sin(X)
        return (u, v)


class CouetteShear(VelocityField):
    """Linear Couette shear velocity field (2-D).

    Velocity field::

        u(x, y) = γ̇ (y − y_mid)
        v(x, y) = 0

    where ``y_mid = LY / 2`` (domain mid-plane) and ``γ̇ = gamma_dot``.
    This drives u = −U at y = 0 and u = +U at y = LY with U = γ̇ LY / 2.

    Parameters
    ----------
    gamma_dot : float
        Shear rate γ̇  (1/time).
    LY : float
        Domain height (used to compute y_mid).
    """

    def __init__(self, gamma_dot: float, LY: float) -> None:
        self.gamma_dot = float(gamma_dot)
        self.LY = float(LY)

    def compute(self, *coords: np.ndarray, t: float = 0.0) -> tuple:
        if len(coords) != 2:
            raise ValueError("CouetteShear.compute: only 2-D grids supported.")
        xp = _xp_of(coords[0])
        X, Y = coords
        y_mid = 0.5 * self.LY
        u = self.gamma_dot * (Y - y_mid)
        v = xp.zeros_like(Y)
        return (u, v)


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

    if field_type == "single_vortex":
        return SingleVortex(period=float(d.get("period", 1.0)))

    if field_type == "double_shear_layer":
        return DoubleShearLayer(
            delta=float(d.get("delta", 0.05)),
            eps=float(d.get("eps", 0.05)),
        )

    if field_type == "couette_shear":
        return CouetteShear(
            gamma_dot=float(d["gamma_dot"]),
            LY=float(d["LY"]),
        )

    raise ValueError(
        f"Unknown velocity_field type '{field_type}'. "
        "Supported: 'rigid_rotation', 'uniform', 'single_vortex', 'double_shear_layer', "
        "'couette_shear'."
    )
