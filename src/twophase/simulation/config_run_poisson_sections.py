"""Poisson/PPE parsing helpers for run-section operator settings."""

from __future__ import annotations

from .config_constants import (
    _PPE_DISCRETIZATIONS,
    _PPE_TO_PRESSURE_SCHEME,
    _POISSON_COEFFICIENT_ALIASES,
    _POISSON_COEFFICIENTS,
    _POISSON_INTERFACE_COUPLING_ALIASES,
    _POISSON_INTERFACE_COUPLINGS,
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
        poisson_operator.get("discretization", "fvm"),
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

    (
        ppe_solver,
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
        "ppe_solver": ppe_solver,
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
    }
