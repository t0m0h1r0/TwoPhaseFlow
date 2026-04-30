"""Compatibility exports for interface-stress closure helpers."""

# DO NOT DELETE: historical import path retained after the affine face-jump
# helpers moved to twophase.coupling.interface_stress_closure.

from ..coupling.interface_stress_closure import (
    InterfaceStressContext,
    build_interface_stress_context,
    build_young_laplace_interface_stress_context,
    interface_stress_context_is_active,
    signed_pressure_jump_gradient,
)

__all__ = [
    "InterfaceStressContext",
    "build_interface_stress_context",
    "build_young_laplace_interface_stress_context",
    "interface_stress_context_is_active",
    "signed_pressure_jump_gradient",
]
