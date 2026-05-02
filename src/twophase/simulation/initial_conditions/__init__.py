"""
initial_conditions — initial CLS field and prescribed velocity from primitives.

Public API
----------
Shape primitives (initial CLS ψ field):

InitialConditionBuilder
    Combines shape primitives into a CLS ψ field via SDF union/subtraction.

Circle
    Circular (2-D) or spherical (3-D) region.

Ellipse
    Elliptical 2-D region for Rayleigh-Lamb droplet oscillation probes.

Rectangle
    Axis-aligned box region.

HalfSpace
    Half-space region defined by a hyperplane.

SinusoidalInterface
    Half-space bounded by a sinusoidal curve (2-D).  Used for
    Rayleigh–Taylor and capillary-wave initial conditions.

shape_from_dict
    Deserialise a shape from a plain dict (YAML fragment).

Velocity field primitives (prescribed external velocity):

VelocityField
    Abstract base for prescribed velocity field primitives.

RigidRotation
    Solid-body rotation: u = -ω(y-cy), v = ω(x-cx).  Used for Zalesak test.

UniformFlow
    Spatially uniform constant velocity.

velocity_field_from_dict
    Deserialise a velocity field from a plain dict (YAML fragment).

Usage
-----
::

    from twophase.simulation.initial_conditions import (
        InitialConditionBuilder, Circle, Rectangle, HalfSpace,
        RigidRotation, velocity_field_from_dict,
    )

    builder = (
        InitialConditionBuilder(background_phase='gas')
        .add(Circle(center=(0.5, 0.5), radius=0.25, interior_phase='liquid'))
    )
    psi = builder.build(grid, eps)

    vf = RigidRotation(center=(0.5, 0.5), period=1.0)
    u, v = vf.compute(X, Y, t=0.0)
"""

from .shapes import (
    Circle,
    Ellipse,
    HalfSpace,
    PerturbedCircle,
    Rectangle,
    SinusoidalInterface,
    ZalesakDisk,
    shape_from_dict,
)
from .builder import InitialConditionBuilder
from .velocity_fields import VelocityField, RigidRotation, UniformFlow, velocity_field_from_dict

__all__ = [
    # shape primitives
    "InitialConditionBuilder",
    "Circle",
    "Ellipse",
    "Rectangle",
    "HalfSpace",
    "SinusoidalInterface",
    "PerturbedCircle",
    "ZalesakDisk",
    "shape_from_dict",
    # velocity field primitives
    "VelocityField",
    "RigidRotation",
    "UniformFlow",
    "velocity_field_from_dict",
]
