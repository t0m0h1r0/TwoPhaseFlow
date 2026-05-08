"""Compatibility constants for experiment config parsing."""

_ADVECTION_SCHEMES = ("dissipative_ccd", "fccd_nodal", "fccd_flux")
_ADVECTION_SCHEME_ALIASES = {"fccd": "fccd_flux"}
_CONVECTION_SCHEMES = ("ccd", "fccd_nodal", "fccd_flux", "uccd6")
_CONVECTION_SCHEME_ALIASES = {"fccd": "fccd_flux"}
_REINIT_METHODS = (
    "split", "unified", "dgr", "hybrid",
    "eikonal", "eikonal_xi", "eikonal_fmm", "ridge_eikonal",
)
_PROJECTION_MODES = (
    "standard", "variable_density", "gfm", "consistent_gfm",
)
_PROJECTION_MODE_ALIASES = {
    "variable_density_only": "variable_density",
}
_PROJECTION_TO_REPROJECT_MODE = {
    "standard": "legacy",
    "variable_density": "variable_density_only",
    "gfm": "gfm",
    "consistent_gfm": "consistent_gfm",
}
_PPE_SCHEMES = (
    "fd_direct", "fd_iterative", "fvm_iterative", "fvm_direct", "fccd_iterative",
)
_PPE_DISCRETIZATION_SOLVERS = {
    ("fd", "direct"): "fd_direct",
    ("fd", "iterative"): "fd_iterative",
    ("fvm", "iterative"): "fvm_iterative",
    ("fvm", "direct"): "fvm_direct",
    ("fccd", "iterative"): "fccd_iterative",
}
_PPE_TO_PRESSURE_SCHEME = {
    "fd_direct": "fd_direct",
    "fd_iterative": "fd_matrixfree",
    "fvm_iterative": "fvm_matrixfree",
    "fvm_direct": "fvm_spsolve",
    "fccd_iterative": "fccd_matrixfree",
}
_PPE_DISCRETIZATIONS = ("fvm", "fccd")
_POISSON_COEFFICIENTS = ("phase_density", "variable_density", "phase_separated")
_POISSON_COEFFICIENT_ALIASES = {
    "variable_density": "phase_density",
    "phase_separated_density": "phase_separated",
    "split_phase": "phase_separated",
}
_POISSON_INTERFACE_COUPLINGS = ("none", "jump_decomposition", "affine_jump")
_POISSON_INTERFACE_COUPLING_ALIASES = {
    "pressure_jump": "affine_jump",
    "jump": "affine_jump",
    "interface_stress": "affine_jump",
    "jump_aware": "affine_jump",
    "legacy_jump": "jump_decomposition",
    "legacy_jump_decomposition": "jump_decomposition",
}
_CAPILLARY_RANGE_PROJECTION_MODES = (
    "auto",
    "none",
    "range_projected",
    "component_hodge_augmented",
)
_CAPILLARY_FORCE_SOURCES = ("curvature_jump", "closed_interface_riesz")
_CAPILLARY_FORCE_SOURCE_ALIASES = {
    "curvature": "curvature_jump",
    "scalar_jump": "curvature_jump",
    "closed_interface": "closed_interface_riesz",
}
_CAPILLARY_REACTION_PROJECTION_MODES = (
    "none",
    "pressure_component_hodge",
)
_CAPILLARY_REACTION_PROJECTION_ALIASES = {
    "component_hodge": "pressure_component_hodge",
    "component": "pressure_component_hodge",
}
_CAPILLARY_RANGE_PROJECTION_ALIASES = {
    "default": "auto",
    "off": "none",
    "false": "none",
    "disabled": "none",
    "on": "range_projected",
    "true": "range_projected",
    "range": "range_projected",
    "component": "component_hodge_augmented",
    "component_augmented": "component_hodge_augmented",
    "augmented": "component_hodge_augmented",
}
_PRESSURE_FORCE_CONTRACTS = ("raw_compact_gradient", "variational_adjoint")
_PRESSURE_FORCE_CONTRACT_ALIASES = {
    "raw": "raw_compact_gradient",
    "raw_gradient": "raw_compact_gradient",
    "raw_compact": "raw_compact_gradient",
    "fccd_gradient": "raw_compact_gradient",
    "variational": "variational_adjoint",
    "adjoint": "variational_adjoint",
    "pressure_adjoint": "variational_adjoint",
}
_SCALAR_OPERATOR_PAIRINGS = (
    "legacy",
    "require_certified",
    "variational_operator",
)
_SCALAR_OPERATOR_PAIRING_ALIASES = {
    "old": "legacy",
    "raw": "legacy",
    "certified": "require_certified",
    "require": "require_certified",
    "variational": "variational_operator",
    "l_var": "variational_operator",
}
_SURFACE_TENSION_SCHEMES = ("csf", "pressure_jump", "none")
_SURFACE_TENSION_ALIASES = {
    "gfm_jump": "pressure_jump",
    "ppe_jump": "pressure_jump",
}
_VISCOUS_TIME_SCHEMES = ("forward_euler", "crank_nicolson", "implicit_bdf2")
_VISCOUS_SOLVERS = ("defect_correction", "gmres")
_VISCOUS_SOLVER_ALIASES = {
    "dc": "defect_correction",
    "viscous_dc": "defect_correction",
    "defect-correction": "defect_correction",
}
_VISCOUS_DC_LOW_OPERATORS = ("component", "scalar")
_VISCOUS_DC_LOW_OPERATOR_ALIASES = {
    "componentwise": "component",
    "tensor": "component",
    "isotropic": "scalar",
}
_INTERFACE_TIME_SCHEMES = ("tvd_rk3",)
_MOMENTUM_PREDICTORS = ("projection_predictor_corrector",)
_CONVECTION_TIME_SCHEMES = ("ab2", "forward_euler", "imex_bdf2")
_MOMENTUM_FORMS = ("primitive_velocity", "conservative_common_flux")
_VISCOUS_SPATIAL_SCHEMES = ("conservative_stress", "ccd_bulk", "ccd_stress_legacy")
_VISCOUS_SPATIAL_ALIASES = {
    "stress_divergence": "conservative_stress",
    "low_order_conservative": "conservative_stress",
    "ccd": "ccd_bulk",
    "ccd_legacy": "ccd_stress_legacy",
}
_CURVATURE_SCHEMES = (
    "psi_direct_filtered",
    "face_implicit",
    "transport_variational",
    "transport_variational_p2",
    "transport_variational_p2_midpoint",
    "transport_variational_p2_discrete_gradient",
    "transport_variational_p2_ale_discrete_gradient",
)
_CURVATURE_SCHEME_ALIASES = {
    "psi_direct": "psi_direct_filtered",
    "psi_direct_hfe": "psi_direct_filtered",
}
_MOMENTUM_PREDICTOR_ALIASES = {
    "fractional_step": "projection_predictor_corrector",
    "pressure_correction": "projection_predictor_corrector",
}
_MOMENTUM_GRADIENT_SCHEMES = ("ccd", "fccd_flux", "fccd_nodal")
_MOMENTUM_GRADIENT_ALIASES = {
    "projection_consistent": "ccd",
    "fccd": "fccd_flux",
}
_PPE_SOLVER_KINDS = ("iterative", "direct", "defect_correction")
_PPE_ITERATION_METHODS = ("gmres", "cg")
_PPE_PRECONDITIONERS = ("jacobi", "line_pcr", "none")
