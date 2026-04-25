"""Compatibility constants for experiment config parsing."""

_ADVECTION_SCHEMES = ("dissipative_ccd", "weno5", "fccd_nodal", "fccd_flux")
_ADVECTION_SCHEME_ALIASES = {"fccd": "fccd_flux"}
_CONVECTION_SCHEMES = ("ccd", "fccd_nodal", "fccd_flux", "uccd6")
_CONVECTION_SCHEME_ALIASES = {"fccd": "fccd_flux"}
_REINIT_METHODS = (
    "split", "unified", "dgr", "hybrid",
    "eikonal", "eikonal_xi", "eikonal_fmm", "ridge_eikonal",
)
_PROJECTION_MODES = ("standard", "variable_density", "iim", "gfm")
_PROJECTION_MODE_ALIASES = {
    "consistent_iim": "iim",
    "consistent_gfm": "gfm",
}
_PROJECTION_TO_REPROJECT_MODE = {
    "standard": "legacy",
    "variable_density": "variable_density_only",
    "iim": "iim",
    "gfm": "gfm",
}
_PPE_SCHEMES = ("fvm_iterative", "fvm_direct", "fccd_iterative")
_PPE_DISCRETIZATION_SOLVERS = {
    ("fvm", "iterative"): "fvm_iterative",
    ("fvm", "direct"): "fvm_direct",
    ("fccd", "iterative"): "fccd_iterative",
}
_PPE_TO_PRESSURE_SCHEME = {
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
_POISSON_INTERFACE_COUPLINGS = ("none", "jump_decomposition")
_POISSON_INTERFACE_COUPLING_ALIASES = {
    "pressure_jump": "jump_decomposition",
    "jump": "jump_decomposition",
}
_SURFACE_TENSION_SCHEMES = ("csf", "pressure_jump", "none")
_SURFACE_TENSION_ALIASES = {
    "gfm_jump": "pressure_jump",
    "ppe_jump": "pressure_jump",
}
_VISCOUS_TIME_SCHEMES = ("forward_euler", "crank_nicolson", "implicit_bdf2")
_INTERFACE_TIME_SCHEMES = ("tvd_rk3",)
_MOMENTUM_PREDICTORS = ("projection_predictor_corrector",)
_CONVECTION_TIME_SCHEMES = ("ab2", "forward_euler", "imex_bdf2")
_MOMENTUM_FORMS = ("primitive_velocity",)
_VISCOUS_SPATIAL_SCHEMES = ("conservative_stress", "ccd_bulk", "ccd_stress_legacy")
_VISCOUS_SPATIAL_ALIASES = {
    "stress_divergence": "conservative_stress",
    "low_order_conservative": "conservative_stress",
    "ccd": "ccd_bulk",
    "ccd_legacy": "ccd_stress_legacy",
}
_CURVATURE_SCHEMES = ("psi_direct_hfe",)
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
_PPE_ITERATION_METHODS = ("gmres",)
_PPE_PRECONDITIONERS = ("jacobi", "line_pcr", "none")
