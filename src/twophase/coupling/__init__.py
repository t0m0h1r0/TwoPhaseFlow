# §8: Pressure-velocity coupling — GFM, PPE RHS, velocity correction
from .capillary_geometry import apply_wall_compatible_curvature
from .closed_interface_geometry import (
    fixed_stratum_directional_derivative_check,
    liquid_area_2d,
    liquid_area_gradient_2d,
    trace_surface_length_2d,
    trace_surface_length_gradient_2d,
)
from .closed_interface_stratum import (
    ClosedInterfaceStratum,
    build_closed_interface_stratum,
)
from .gfm import GFMCorrector
from .interface_stress_closure import (
    InterfaceStressContext,
    build_interface_stress_context,
    build_young_laplace_interface_stress_context,
    evaluate_interface_face_curvature_lg,
    interface_stress_context_is_active,
    signed_pressure_jump_gradient,
)
from .velocity_corrector import VelocityCorrector
from .ppe_rhs_gfm import PPERHSBuilderGFM

__all__ = [
    "GFMCorrector",
    "InterfaceStressContext",
    "VelocityCorrector",
    "ClosedInterfaceStratum",
    "PPERHSBuilderGFM",
    "apply_wall_compatible_curvature",
    "build_interface_stress_context",
    "build_closed_interface_stratum",
    "build_young_laplace_interface_stress_context",
    "evaluate_interface_face_curvature_lg",
    "fixed_stratum_directional_derivative_check",
    "interface_stress_context_is_active",
    "liquid_area_2d",
    "liquid_area_gradient_2d",
    "signed_pressure_jump_gradient",
    "trace_surface_length_2d",
    "trace_surface_length_gradient_2d",
]
