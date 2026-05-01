# §8: Pressure-velocity coupling — GFM, PPE RHS, velocity correction
from .capillary_geometry import apply_wall_compatible_curvature
from .gfm import GFMCorrector
from .interface_stress_closure import (
    InterfaceStressContext,
    build_interface_stress_context,
    build_young_laplace_interface_stress_context,
    interface_stress_context_is_active,
    signed_pressure_jump_gradient,
)
from .velocity_corrector import VelocityCorrector
from .ppe_rhs_gfm import PPERHSBuilderGFM

__all__ = [
    "GFMCorrector",
    "InterfaceStressContext",
    "VelocityCorrector",
    "PPERHSBuilderGFM",
    "apply_wall_compatible_curvature",
    "build_interface_stress_context",
    "build_young_laplace_interface_stress_context",
    "interface_stress_context_is_active",
    "signed_pressure_jump_gradient",
]
