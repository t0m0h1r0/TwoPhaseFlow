"""Shared option canonicalization for NS config parsing and runtime setup."""

from __future__ import annotations

from .config_constants import (
    _CONVECTION_TIME_SCHEMES,
    _MOMENTUM_GRADIENT_ALIASES,
    _MOMENTUM_GRADIENT_SCHEMES,
    _PPE_TO_PRESSURE_SCHEME,
    _VISCOUS_TIME_SCHEMES,
)
from .config_sections import validate_choice

CONVECTION_TIME_SCHEME_ALIASES = {
    "explicit": "ab2",
    "adams_bashforth_2": "ab2",
    "adams_bashforth": "ab2",
    "ab_2": "ab2",
    "bdf2": "imex_bdf2",
    "ext2_bdf2": "imex_bdf2",
    "imex-bdf2": "imex_bdf2",
    "forward_euler": "forward_euler",
    "euler": "forward_euler",
}
VISCOUS_TIME_SCHEME_ALIASES = {
    "explicit": "forward_euler",
    "euler": "forward_euler",
    "forward-euler": "forward_euler",
    "cn": "crank_nicolson",
    "crank-nicolson": "crank_nicolson",
    "bdf2": "implicit_bdf2",
    "implicit-bdf2": "implicit_bdf2",
    "imex_bdf2": "implicit_bdf2",
    "imex-bdf2": "implicit_bdf2",
}
PRESSURE_JUMP_PPE_COEFFICIENT = "phase_separated"
PRESSURE_JUMP_INTERFACE_COUPLING = "jump_decomposition"


def canonicalize_convection_time_scheme(raw) -> str:
    """Return the canonical convection time integrator name."""
    value = str(raw).strip().lower()
    canonical = CONVECTION_TIME_SCHEME_ALIASES.get(value, value)
    if canonical not in _CONVECTION_TIME_SCHEMES:
        raise ValueError(
            "Unsupported convection_time_scheme="
            f"{canonical!r}; use ab2|forward_euler|imex_bdf2."
        )
    return canonical


def canonicalize_viscous_time_scheme(raw) -> str:
    """Return the canonical viscous time integrator name."""
    value = str(raw).strip().lower()
    canonical = VISCOUS_TIME_SCHEME_ALIASES.get(value, value)
    if canonical not in _VISCOUS_TIME_SCHEMES:
        raise ValueError(
            "Unsupported viscous_time_scheme="
            f"{canonical!r}; use forward_euler|crank_nicolson|implicit_bdf2."
        )
    return canonical


def canonicalize_momentum_gradient_scheme(raw, *, path: str | None = None) -> str:
    """Return the canonical momentum/pressure gradient scheme."""
    canonical = _MOMENTUM_GRADIENT_ALIASES.get(str(raw).strip().lower(), raw)
    if path is not None:
        return validate_choice(canonical, _MOMENTUM_GRADIENT_SCHEMES, path)
    value = str(canonical).strip().lower()
    if value not in _MOMENTUM_GRADIENT_SCHEMES:
        raise ValueError(
            "Unsupported momentum_gradient_scheme="
            f"{value!r}; use ccd|fccd_flux|fccd_nodal."
        )
    return value


def canonicalize_ppe_solver_name(raw_ppe, *, ppe_aliases: dict, ppe_registry: dict) -> str:
    """Normalize the PPE solver name against the active registry."""
    value = str(raw_ppe).strip().lower()
    ppe_solver_name = ppe_aliases.get(value, value)
    if ppe_solver_name not in ppe_registry:
        raise ValueError(
            f"Unsupported ppe_solver={value!r}. "
            "Use fvm_iterative|fvm_direct|fccd_iterative."
        )
    return ppe_solver_name


def pressure_scheme_for_ppe_solver(ppe_solver_name: str) -> str:
    """Map a canonical PPE solver name to the internal pressure scheme."""
    return _PPE_TO_PRESSURE_SCHEME[ppe_solver_name]


def validate_pressure_jump_ppe_compatibility(
    *,
    surface_tension_scheme: str,
    ppe_coefficient_scheme: str,
    ppe_interface_coupling_scheme: str,
    coefficient_error: str,
    interface_error: str,
) -> None:
    """Validate the required PPE settings for pressure-jump surface tension."""
    if str(surface_tension_scheme).strip().lower() != "pressure_jump":
        return
    if ppe_coefficient_scheme != PRESSURE_JUMP_PPE_COEFFICIENT:
        raise ValueError(coefficient_error)
    if ppe_interface_coupling_scheme != PRESSURE_JUMP_INTERFACE_COUPLING:
        raise ValueError(interface_error)


def canonicalize_surface_tension_gradient_scheme(
    *,
    surface_tension_scheme: str,
    surface_tension_gradient_scheme,
    momentum_gradient_scheme: str,
    path: str | None = None,
) -> str:
    """Return the canonical capillary-force gradient scheme."""
    if str(surface_tension_scheme).strip().lower() == "pressure_jump":
        if surface_tension_gradient_scheme not in {None, "none"}:
            if path is None:
                raise ValueError(
                    "surface_tension_gradient_scheme must be omitted or 'none' "
                    "when surface_tension_scheme='pressure_jump'"
                )
            raise ValueError(
                f"{path} must be omitted "
                "when surface_tension.formulation='pressure_jump'; "
                "the jump is applied in the PPE, not as σκ∇ψ."
            )
        return "none"

    raw_scheme = (
        momentum_gradient_scheme
        if surface_tension_gradient_scheme is None
        else surface_tension_gradient_scheme
    )
    return canonicalize_momentum_gradient_scheme(raw_scheme, path=path)
