"""Poisson/PPE parsing helpers for run-section operator settings."""

from __future__ import annotations

from .config_constants import (
    _CAPILLARY_RANGE_PROJECTION_ALIASES,
    _CAPILLARY_RANGE_PROJECTION_MODES,
    _CAPILLARY_REACTION_PROJECTION_ALIASES,
    _CAPILLARY_REACTION_PROJECTION_MODES,
    _PPE_DISCRETIZATIONS,
    _PPE_TO_PRESSURE_SCHEME,
    _POISSON_COEFFICIENT_ALIASES,
    _POISSON_COEFFICIENTS,
    _POISSON_INTERFACE_COUPLING_ALIASES,
    _POISSON_INTERFACE_COUPLINGS,
    _PRESSURE_FORCE_CONTRACT_ALIASES,
    _PRESSURE_FORCE_CONTRACTS,
    _PRESSURE_HISTORY_EXTRAPOLATION_ALIASES,
    _PRESSURE_HISTORY_EXTRAPOLATIONS,
    _PRESSURE_HISTORY_MODE_ALIASES,
    _PRESSURE_HISTORY_MODES,
    _SCALAR_OPERATOR_PAIRING_ALIASES,
    _SCALAR_OPERATOR_PAIRINGS,
)
from .config_run_ppe_sections import parse_ppe_solver_config
from .config_sections import validate_choice


def parse_run_poisson_settings(*, layout: dict, projection: dict) -> dict:
    """Parse Poisson operator and PPE solver settings for `parse_run_operator_settings`."""
    poisson = projection["poisson"]
    poisson_operator = poisson.get("operator", {})
    if not poisson_operator and ("discretization" in poisson or "coefficient" in poisson):
        poisson_operator = {
            key: poisson[key]
            for key in ("discretization", "coefficient")
            if key in poisson
        }
    poisson_discretization = validate_choice(
        poisson_operator.get("discretization", "fccd"),
        _PPE_DISCRETIZATIONS,
        layout["paths"]["poisson_discretization"],
    )
    if "coefficient" not in poisson_operator:
        raise ValueError(
            f"{layout['paths']['poisson_coefficient']} is required; "
            "use 'phase_separated' for SP-M or 'phase_density' for mixture-density PPE."
        )
    poisson_coefficient = validate_choice(
        _POISSON_COEFFICIENT_ALIASES.get(
            str(poisson_operator["coefficient"]).strip().lower(),
            poisson_operator["coefficient"],
        ),
        _POISSON_COEFFICIENTS,
        layout["paths"]["poisson_coefficient"],
    )
    coupling_default = "affine_jump" if poisson_coefficient == "phase_separated" else "none"
    poisson_interface_coupling = validate_choice(
        _POISSON_INTERFACE_COUPLING_ALIASES.get(
            str(poisson_operator.get("interface_coupling", coupling_default)).strip().lower(),
            poisson_operator.get("interface_coupling", coupling_default),
        ),
        _POISSON_INTERFACE_COUPLINGS,
        layout["paths"]["poisson_interface_coupling"],
    )
    if poisson_coefficient == "phase_density" and poisson_interface_coupling != "none":
        raise ValueError(
            f"{layout['paths']['poisson_interface_coupling']} must be 'none' "
            "when poisson coefficient is 'phase_density'."
        )
    capillary_projection_default = (
        "component_hodge_augmented"
        if poisson_interface_coupling == "affine_jump"
        else "none"
    )
    capillary_range_projection = validate_choice(
        _CAPILLARY_RANGE_PROJECTION_ALIASES.get(
            str(poisson_operator.get("capillary_range_projection", capillary_projection_default))
            .strip()
            .lower(),
            poisson_operator.get("capillary_range_projection", capillary_projection_default),
        ),
        _CAPILLARY_RANGE_PROJECTION_MODES,
        layout["paths"]["poisson_capillary_range_projection"],
    )
    if (
        capillary_range_projection != "none"
        and poisson_interface_coupling != "affine_jump"
    ):
        raise ValueError(
            f"{layout['paths']['poisson_capillary_range_projection']} requires "
            "poisson.operator.interface_coupling='affine_jump'."
        )
    capillary_reaction_projection = validate_choice(
        _CAPILLARY_REACTION_PROJECTION_ALIASES.get(
            str(poisson_operator.get("capillary_reaction_projection", "none"))
            .strip()
            .lower(),
            poisson_operator.get("capillary_reaction_projection", "none"),
        ),
        _CAPILLARY_REACTION_PROJECTION_MODES,
        layout["paths"]["poisson_capillary_reaction_projection"],
    )
    if (
        capillary_reaction_projection != "none"
        and poisson_interface_coupling != "affine_jump"
    ):
        raise ValueError(
            f"{layout['paths']['poisson_capillary_reaction_projection']} requires "
            "poisson.operator.interface_coupling='affine_jump'."
        )
    pressure_force_contract = validate_choice(
        _PRESSURE_FORCE_CONTRACT_ALIASES.get(
            str(poisson_operator.get("pressure_force_contract", "raw_compact_gradient"))
            .strip()
            .lower(),
            poisson_operator.get("pressure_force_contract", "raw_compact_gradient"),
        ),
        _PRESSURE_FORCE_CONTRACTS,
        "numerics.projection.poisson.operator.pressure_force_contract",
    )
    scalar_operator_pairing = validate_choice(
        _SCALAR_OPERATOR_PAIRING_ALIASES.get(
            str(poisson_operator.get("scalar_operator_pairing", "legacy"))
            .strip()
            .lower(),
            poisson_operator.get("scalar_operator_pairing", "legacy"),
        ),
        _SCALAR_OPERATOR_PAIRINGS,
        "numerics.projection.poisson.operator.scalar_operator_pairing",
    )
    if (
        pressure_force_contract == "raw_compact_gradient"
        and scalar_operator_pairing != "legacy"
    ):
        raise ValueError(
            "poisson.operator.scalar_operator_pairing requires "
            "pressure_force_contract='variational_adjoint' unless using legacy."
        )
    pressure_history = projection.get("pressure_history", {}) or {}
    pressure_history_mode = validate_choice(
        _PRESSURE_HISTORY_MODE_ALIASES.get(
            str(pressure_history.get("form", "face_acceleration")).strip().lower(),
            pressure_history.get("form", "face_acceleration"),
        ),
        _PRESSURE_HISTORY_MODES,
        "numerics.projection.pressure_history.form",
    )
    pressure_history_extrapolation = validate_choice(
        _PRESSURE_HISTORY_EXTRAPOLATION_ALIASES.get(
            str(pressure_history.get("extrapolation", "constant")).strip().lower(),
            pressure_history.get("extrapolation", "constant"),
        ),
        _PRESSURE_HISTORY_EXTRAPOLATIONS,
        "numerics.projection.pressure_history.extrapolation",
    )
    if (
        pressure_history_mode == "pressure_coordinate"
        and pressure_force_contract != "variational_adjoint"
    ):
        raise ValueError(
            "numerics.projection.pressure_history.form='pressure_coordinate' "
            "requires poisson.operator.pressure_force_contract='variational_adjoint'."
        )

    (
        ppe_solver,
        ppe_dc_base_solver,
        ppe_iteration_method,
        ppe_tolerance,
        ppe_max_iterations,
        ppe_restart,
        ppe_preconditioner,
        ppe_pcr_stages,
        ppe_c_tau,
        ppe_defect_correction,
        ppe_dc_max_iterations,
        ppe_dc_tolerance,
        ppe_dc_relaxation,
        ppe_dc_fail_close,
    ) = parse_ppe_solver_config(
        poisson["solver"],
        layout["paths"]["poisson_solver"],
        poisson_discretization,
        layout["paths"]["poisson_discretization"],
    )
    return {
        "poisson_discretization": poisson_discretization,
        "poisson_coefficient": poisson_coefficient,
        "poisson_interface_coupling": poisson_interface_coupling,
        "capillary_range_projection": capillary_range_projection,
        "capillary_reaction_projection": capillary_reaction_projection,
        "pressure_force_contract": pressure_force_contract,
        "scalar_operator_pairing": scalar_operator_pairing,
        "pressure_history_mode": pressure_history_mode,
        "pressure_history_extrapolation": pressure_history_extrapolation,
        "ppe_solver": ppe_solver,
        "ppe_dc_base_solver": ppe_dc_base_solver,
        "pressure_scheme": _PPE_TO_PRESSURE_SCHEME[ppe_solver],
        "ppe_iteration_method": ppe_iteration_method,
        "ppe_tolerance": ppe_tolerance,
        "ppe_max_iterations": ppe_max_iterations,
        "ppe_restart": ppe_restart,
        "ppe_preconditioner": ppe_preconditioner,
        "ppe_pcr_stages": ppe_pcr_stages,
        "ppe_c_tau": ppe_c_tau,
        "ppe_defect_correction": ppe_defect_correction,
        "ppe_dc_max_iterations": ppe_dc_max_iterations,
        "ppe_dc_tolerance": ppe_dc_tolerance,
        "ppe_dc_relaxation": ppe_dc_relaxation,
        "ppe_dc_fail_close": ppe_dc_fail_close,
    }
