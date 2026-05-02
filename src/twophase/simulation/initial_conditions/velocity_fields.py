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
    composite        — superpose a base field and perturbation fields
    sinusoidal_perturbation — one-component sinusoidal perturbation
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Sequence, Tuple

import numpy as np

from ...backend import array_namespace


def _axis_index(value, *, name: str) -> int:
    """Convert x|y|z or an integer-like value to an axis index."""
    if value is None:
        raise ValueError(f"{name} is required.")
    if isinstance(value, str):
        axis = value.lower()
        if axis in {"x", "0"}:
            return 0
        if axis in {"y", "1"}:
            return 1
        if axis in {"z", "2"}:
            return 2
        raise ValueError(f"{name} must be x|y|z|0|1|2.")
    return int(value)


def _wave_wavelength(data: dict, *, owner: str) -> float:
    """Resolve wavelength from an explicit value or mode/length pair."""
    if "wavelength" in data:
        wavelength = float(data["wavelength"])
    else:
        mode = int(data.get("mode", 0))
        if mode <= 0:
            raise ValueError(f"{owner}: provide 'wavelength' or positive 'mode'.")
        length = float(data.get("length", data.get("domain_length", 1.0)))
        if length <= 0.0:
            raise ValueError(f"{owner}: length must be positive.")
        wavelength = length / float(mode)
    if wavelength <= 0.0:
        raise ValueError(f"{owner}: wavelength must be positive.")
    return wavelength


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
        xp = array_namespace(coords[0])
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
        xp = array_namespace(coords[0])
        return tuple(xp.full_like(c, v) for c, v in zip(coords, self.velocity))


class CompositeVelocityField(VelocityField):
    """Velocity field formed by summing independent component fields."""

    def __init__(self, fields: Sequence[VelocityField]) -> None:
        self.fields: Tuple[VelocityField, ...] = tuple(fields)

    def compute(self, *coords: np.ndarray, t: float = 0.0) -> Tuple[np.ndarray, ...]:
        """Return the component-wise sum of all configured fields."""
        if not coords:
            raise ValueError("CompositeVelocityField.compute: coords must be non-empty.")
        xp = array_namespace(coords[0])
        total_components = [xp.zeros_like(coord) for coord in coords]
        for field in self.fields:
            field_components = field.compute(*coords, t=t)
            if len(field_components) != len(total_components):
                raise ValueError(
                    "CompositeVelocityField.compute: component count mismatch."
                )
            total_components = [
                total_component + field_component
                for total_component, field_component
                in zip(total_components, field_components)
            ]
        return tuple(total_components)


class SinusoidalPerturbation(VelocityField):
    """One-component sinusoidal velocity perturbation."""

    def __init__(
        self,
        component: int,
        axis: int,
        amplitude: float,
        wavelength: float,
        *,
        phase: float = 0.0,
        profile: str = "sin",
        offset: float = 0.0,
    ) -> None:
        if wavelength <= 0.0:
            raise ValueError("SinusoidalPerturbation: wavelength must be positive.")
        profile_name = str(profile).lower()
        if profile_name not in {"sin", "cos"}:
            raise ValueError("SinusoidalPerturbation: profile must be sin|cos.")
        self.component = int(component)
        self.axis = int(axis)
        self.amplitude = float(amplitude)
        self.wavelength = float(wavelength)
        self.phase = float(phase)
        self.profile = profile_name
        self.offset = float(offset)

    def compute(self, *coords: np.ndarray, t: float = 0.0) -> Tuple[np.ndarray, ...]:
        """Return zeros except for the configured perturbation component."""
        if self.component < 0 or self.component >= len(coords):
            raise ValueError(
                "SinusoidalPerturbation.compute: component index is outside grid ndim."
            )
        if self.axis < 0 or self.axis >= len(coords):
            raise ValueError(
                "SinusoidalPerturbation.compute: wave axis is outside grid ndim."
            )
        xp = array_namespace(coords[0])
        argument = 2.0 * xp.pi * coords[self.axis] / self.wavelength + self.phase
        if self.profile == "sin":
            perturbation = self.amplitude * xp.sin(argument)
        else:
            perturbation = self.amplitude * xp.cos(argument)
        if self.offset != 0.0:
            perturbation = perturbation + self.offset
        components = [xp.zeros_like(coord) for coord in coords]
        components[self.component] = perturbation
        return tuple(components)


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
        xp = array_namespace(coords[0])
        X, Y = coords
        T = self.period
        cos_t = float(np.cos(np.pi * t / T))
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
        xp = array_namespace(coords[0])
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
        xp = array_namespace(coords[0])
        X, Y = coords
        y_mid = 0.5 * self.LY
        u = self.gamma_dot * (Y - y_mid)
        v = xp.zeros_like(Y)
        return (u, v)


def _build_rigid_rotation(data: dict) -> VelocityField:
    return RigidRotation(
        center=data["center"],
        period=float(data.get("period", 1.0)),
    )


def _build_uniform_flow(data: dict) -> VelocityField:
    return UniformFlow(velocity=data["velocity"])


def _build_composite_velocity(data: dict) -> VelocityField:
    field_specs = _composite_field_specs(data)
    return CompositeVelocityField(
        [velocity_field_from_dict(field_spec) for field_spec in field_specs]
    )


def _build_sinusoidal_perturbation(data: dict) -> VelocityField:
    return SinusoidalPerturbation(
        component=_axis_index(
            data.get("component", data.get("direction")),
            name="SinusoidalPerturbation.component",
        ),
        axis=_axis_index(
            data.get("axis", data.get("wave_axis", "x")),
            name="SinusoidalPerturbation.axis",
        ),
        amplitude=float(data["amplitude"]),
        wavelength=_wave_wavelength(data, owner="SinusoidalPerturbation"),
        phase=float(data.get("phase", 0.0)),
        profile=str(data.get("profile", data.get("function", "sin"))),
        offset=float(data.get("offset", 0.0)),
    )


def _build_single_vortex(data: dict) -> VelocityField:
    return SingleVortex(period=float(data.get("period", 1.0)))


def _build_double_shear_layer(data: dict) -> VelocityField:
    return DoubleShearLayer(
        delta=float(data.get("delta", 0.05)),
        eps=float(data.get("eps", 0.05)),
    )


def _build_couette_shear(data: dict) -> VelocityField:
    return CouetteShear(
        gamma_dot=float(data["gamma_dot"]),
        LY=float(data["LY"]),
    )


_VELOCITY_FIELD_BUILDERS: dict[str, Callable[[dict], VelocityField]] = {
    "composite": _build_composite_velocity,
    "superposition": _build_composite_velocity,
    "rigid_rotation": _build_rigid_rotation,
    "uniform": _build_uniform_flow,
    "sinusoidal": _build_sinusoidal_perturbation,
    "sinusoidal_perturbation": _build_sinusoidal_perturbation,
    "single_vortex": _build_single_vortex,
    "double_shear_layer": _build_double_shear_layer,
    "couette_shear": _build_couette_shear,
}


def _composite_field_specs(data: dict) -> list[dict]:
    """Return normalized child specs for a composite velocity field."""
    if "fields" in data and "components" in data:
        raise ValueError("CompositeVelocityField: use either 'fields' or 'components'.")

    specs = []
    base_spec = data.get("base")
    if base_spec is not None:
        specs.append(base_spec)

    specs.extend(data.get("fields", data.get("components", [])) or [])
    specs.extend(data.get("perturbations", []) or [])

    for spec in specs:
        if not isinstance(spec, dict):
            raise ValueError("CompositeVelocityField: child specs must be dicts.")
    return specs


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

        composite::

            base:
              type: uniform
              velocity: [0.0, 0.0]
            perturbations:
              - type: sinusoidal_perturbation
                component: y
                axis: x
                amplitude: 0.01
                mode: 1
                length: 1.0

    Returns
    -------
    field : VelocityField

    Raises
    ------
    ValueError
        Unknown field type or missing required fields.
    """
    data = dict(d)  # コピー（pop で元を壊さない）
    field_type = data.pop("type", None)
    if field_type is None:
        if any(
            key in data
            for key in ("base", "fields", "components", "perturbations")
        ):
            return _build_composite_velocity(data)
        raise ValueError("velocity_field dict must have a 'type' key.")

    builder = _VELOCITY_FIELD_BUILDERS.get(field_type)
    if builder is not None:
        return builder(data)

    supported = "', '".join(_VELOCITY_FIELD_BUILDERS.keys())
    raise ValueError(
        f"Unknown velocity_field type '{field_type}'. "
        f"Supported: '{supported}'."
    )
