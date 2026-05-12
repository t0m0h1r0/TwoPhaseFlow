"""Fail-closed parser gates for interface state-space declarations.

A3 chain:
  Equation: SP-AO promotes the material carrier from diffuse ``psi`` to the
  physical cell volume ``q_C`` with normalized view ``theta_C``.
  Discretization: geometric AO requires hard cell-volume compatibility,
  active-cached projection, GPU-resident active storage, and explicit fallback.
  Code: this parser validates the front-door contract before runtime wiring.

C1 intentionally validates and then blocks geometric runtime construction.
Actual active AO-Fast runtime adapters land only after the C2-C8 gates pass.
"""

from __future__ import annotations

import math
from typing import Any

from .config_models import InterfaceStateSpaceCfg
from .config_sections import validate_choice


def parse_interface_state_space(interface: dict, numerics: dict) -> InterfaceStateSpaceCfg:
    """Parse ``interface.state_space`` and fail-close on ambiguous AO contracts."""
    raw = interface.get("state_space")
    if raw is None:
        _validate_legacy_diffuse_stack(numerics)
        return InterfaceStateSpaceCfg()

    if isinstance(raw, str):
        raw = {"kind": raw}
    if not isinstance(raw, dict):
        raise ValueError("interface.state_space must be a mapping or kind string")
    if "kind" not in raw:
        raise ValueError("interface.state_space.kind is required")

    kind = validate_choice(
        raw["kind"],
        ("diffuse_cls", "geometric_cell_fraction"),
        "interface.state_space.kind",
    )
    if kind == "diffuse_cls":
        _parse_declared_diffuse(raw)
        _validate_legacy_diffuse_stack(numerics)
        return InterfaceStateSpaceCfg()

    return _parse_geometric_cell_fraction_state_space(raw, interface, numerics)


def _parse_declared_diffuse(raw: dict[str, Any]) -> None:
    extras = sorted(set(raw) - {"kind"})
    if extras:
        raise ValueError(
            "interface.state_space.kind='diffuse_cls' must not declare "
            f"geometric keys: {', '.join(extras)}"
        )


def _parse_geometric_cell_fraction_state_space(
    raw: dict[str, Any],
    interface: dict[str, Any],
    numerics: dict[str, Any],
) -> InterfaceStateSpaceCfg:
    gauge = _mapping(raw.get("gauge", {}), "interface.state_space.gauge")
    compatibility = _mapping(
        raw.get("compatibility", {}),
        "interface.state_space.compatibility",
    )
    projection = _mapping(
        compatibility.get("projection", {}),
        "interface.state_space.compatibility.projection",
    )
    gpu_contract = _mapping(
        projection.get("gpu_contract", {}),
        "interface.state_space.compatibility.projection.gpu_contract",
    )
    support_budget = _mapping(
        projection.get("support_budget", {}),
        "interface.state_space.compatibility.projection.support_budget",
    )
    solver = _mapping(
        projection.get("solver", {}),
        "interface.state_space.compatibility.projection.solver",
    )

    conserved_variable = _require_value(
        raw.get("conserved_variable", "q"),
        "q",
        "interface.state_space.conserved_variable",
    )
    normalized_view = _require_value(
        raw.get("normalized_view", "theta"),
        "theta",
        "interface.state_space.normalized_view",
    )
    gauge_variable = _require_value(
        gauge.get("variable", "phi"),
        "phi",
        "interface.state_space.gauge.variable",
    )
    gauge_trace = _require_value(
        gauge.get("trace", "p1_levelset"),
        "p1_levelset",
        "interface.state_space.gauge.trace",
    )
    compatibility_constraint = _require_value(
        compatibility.get("constraint", "hard_cell_volume"),
        "hard_cell_volume",
        "interface.state_space.compatibility.constraint",
    )
    compatibility_units = _require_value(
        compatibility.get("units", "physical_volume"),
        "physical_volume",
        "interface.state_space.compatibility.units",
    )
    projection_implementation = _require_value(
        projection.get("implementation"),
        "active_cached",
        "interface.state_space.compatibility.projection.implementation",
    )
    dense_reference = _require_value(
        projection.get("dense_reference"),
        "test_only",
        "interface.state_space.compatibility.projection.dense_reference",
    )
    _validate_gpu_contract(gpu_contract)
    _require_value(
        projection.get("method", "fixed_stratum_schur"),
        "fixed_stratum_schur",
        "interface.state_space.compatibility.projection.method",
    )
    _require_value(
        projection.get("metric", "screened_gauge_hodge"),
        "screened_gauge_hodge",
        "interface.state_space.compatibility.projection.metric",
    )
    _require_true(
        projection.get("fail_close", True),
        "interface.state_space.compatibility.projection.fail_close",
    )
    _require_value(
        projection.get("trust_region", "sign_margin"),
        "sign_margin",
        "interface.state_space.compatibility.projection.trust_region",
    )
    _positive_float(
        projection.get("residual_tolerance", 1.0e-11),
        "interface.state_space.compatibility.projection.residual_tolerance",
    )
    _require_value(
        projection.get("condition_gate"),
        "fail_close",
        "interface.state_space.compatibility.projection.condition_gate",
    )
    _validate_support_budget(support_budget)
    fallback_policy = _validate_solver_policy(solver)
    _validate_reinitialization(interface)
    _validate_geometric_numerics(numerics)
    return InterfaceStateSpaceCfg(
        kind="geometric_cell_fraction",
        conserved_variable=conserved_variable,
        normalized_view=normalized_view,
        gauge_variable=gauge_variable,
        gauge_trace=gauge_trace,
        compatibility_constraint=compatibility_constraint,
        compatibility_units=compatibility_units,
        projection_implementation=projection_implementation,
        dense_reference=dense_reference,
        gpu_required=True,
        fallback_policy=fallback_policy,
    )


def _validate_gpu_contract(gpu_contract: dict[str, Any]) -> None:
    _require_true(
        gpu_contract.get("required"),
        "interface.state_space.compatibility.projection.gpu_contract.required",
    )
    _require_value(
        gpu_contract.get("active_storage"),
        "struct_of_arrays",
        "interface.state_space.compatibility.projection.gpu_contract.active_storage",
    )
    _require_value(
        gpu_contract.get("inner_host_transfers"),
        "forbidden",
        "interface.state_space.compatibility.projection.gpu_contract.inner_host_transfers",
    )
    _require_value(
        gpu_contract.get("dense_runtime_fallback"),
        "forbidden",
        "interface.state_space.compatibility.projection.gpu_contract.dense_runtime_fallback",
    )
    _require_true(
        gpu_contract.get("record_kernel_counters"),
        "interface.state_space.compatibility.projection.gpu_contract.record_kernel_counters",
    )


def _validate_support_budget(support_budget: dict[str, Any]) -> None:
    for key in ("max_active_ratio", "max_support_stream_ratio", "max_epoch_growth_ratio"):
        value = _positive_float(
            support_budget.get(key),
            f"interface.state_space.compatibility.projection.support_budget.{key}",
        )
        if key != "max_epoch_growth_ratio" and value > 1.0:
            raise ValueError(
                "interface.state_space.compatibility.projection.support_budget."
                f"{key} must be <= 1.0"
            )
    _require_value(
        support_budget.get("on_overrun"),
        "fail_close",
        "interface.state_space.compatibility.projection.support_budget.on_overrun",
    )


def _validate_solver_policy(solver: dict[str, Any]) -> str:
    primary = _require_value(
        solver.get("primary", "active_pcg_newton"),
        solver.get("primary", "active_pcg_newton"),
        "interface.state_space.compatibility.projection.solver.primary",
    )
    if primary not in {"active_pcg_newton", "residual_monotone_dc"}:
        raise ValueError(
            "interface.state_space.compatibility.projection.solver.primary must be "
            "'active_pcg_newton' or 'residual_monotone_dc'"
        )
    _validate_accelerators(
        _mapping(
            solver.get("accelerators", {}),
            "interface.state_space.compatibility.projection.solver.accelerators",
        )
    )
    fallback = _mapping(
        solver.get("fallback", {"policy": "none"}),
        "interface.state_space.compatibility.projection.solver.fallback",
    )
    policy = validate_choice(
        fallback.get("policy", "none"),
        ("none", "explicit_chain"),
        "interface.state_space.compatibility.projection.solver.fallback.policy",
    )
    if policy == "explicit_chain":
        _validate_explicit_chain(fallback)
    return policy


def _validate_accelerators(accelerators: dict[str, Any]) -> None:
    dc_candidate = accelerators.get("dc_candidate")
    if dc_candidate is None:
        return
    dc_candidate = _mapping(
        dc_candidate,
        "interface.state_space.compatibility.projection.solver.accelerators.dc_candidate",
    )
    if bool(dc_candidate.get("enabled", False)):
        _require_value(
            dc_candidate.get("role"),
            "proposal_only",
            "interface.state_space.compatibility.projection.solver."
            "accelerators.dc_candidate.role",
        )
        _require_value(
            dc_candidate.get("on_reject"),
            "discard_candidate",
            "interface.state_space.compatibility.projection.solver."
            "accelerators.dc_candidate.on_reject",
        )


def _validate_explicit_chain(fallback: dict[str, Any]) -> None:
    chain = fallback.get("chain")
    if not isinstance(chain, list) or not chain:
        raise ValueError(
            "interface.state_space.compatibility.projection.solver.fallback."
            "policy=explicit_chain requires non-empty chain"
        )
    for index, transition in enumerate(chain):
        path = (
            "interface.state_space.compatibility.projection.solver.fallback."
            f"chain[{index}]"
        )
        transition = _mapping(transition, path)
        for key in ("from", "to", "triggers", "record_as"):
            if key not in transition:
                raise ValueError(f"{path}.{key} is required")
        triggers = transition["triggers"]
        if not isinstance(triggers, list) or not triggers:
            raise ValueError(f"{path}.triggers must be a non-empty list")


def _validate_reinitialization(interface: dict[str, Any]) -> None:
    reinit = _mapping(interface.get("reinitialization", {}), "interface.reinitialization")
    algorithm = str(reinit.get("algorithm", "none")).strip().lower()
    if algorithm not in {"none", "compatibility_projection"}:
        raise ValueError(
            "geometric_cell_fraction requires interface.reinitialization.algorithm "
            "to be 'none' or 'compatibility_projection'"
        )
    schedule = _mapping(
        reinit.get("schedule", {}),
        "interface.reinitialization.schedule",
    )
    every_steps = _nonnegative_int(
        schedule.get("every_steps", 0),
        "interface.reinitialization.schedule.every_steps",
    )
    if algorithm == "none" and every_steps != 0:
        raise ValueError(
            "geometric_cell_fraction with reinitialization.algorithm='none' "
            "requires schedule.every_steps=0"
        )
    if algorithm == "compatibility_projection" and every_steps <= 0:
        raise ValueError(
            "geometric_cell_fraction compatibility_projection requires "
            "schedule.every_steps > 0"
        )


def _validate_geometric_numerics(numerics: dict[str, Any]) -> None:
    if not all(key in numerics for key in ("interface", "momentum", "projection")):
        raise ValueError(
            "geometric_cell_fraction requires numerics.interface, "
            "numerics.momentum, and numerics.projection"
        )
    interface_num = _mapping(numerics["interface"], "numerics.interface")
    transport = _mapping(interface_num.get("transport"), "numerics.interface.transport")
    _require_value(transport.get("variable"), "q", "numerics.interface.transport.variable")
    _require_value(
        transport.get("spatial"),
        "geometric_swept_volume",
        "numerics.interface.transport.spatial",
    )
    _require_value(
        transport.get("boundedness"),
        "certified",
        "numerics.interface.transport.boundedness",
    )
    _require_true(transport.get("fail_close", True), "numerics.interface.transport.fail_close")

    momentum = _mapping(numerics["momentum"], "numerics.momentum")
    _require_value(momentum.get("form"), "conservative_common_flux", "numerics.momentum.form")
    terms = _mapping(momentum.get("terms", {}), "numerics.momentum.terms")
    surface = _mapping(
        terms.get("surface_tension", {}),
        "numerics.momentum.terms.surface_tension",
    )
    _require_value(
        surface.get("formulation", "pressure_jump"),
        "pressure_jump",
        "numerics.momentum.terms.surface_tension.formulation",
    )
    _require_value(
        surface.get("source"),
        "bundle_virtual_work",
        "numerics.momentum.terms.surface_tension.source",
    )
    closed_interface = _mapping(
        surface.get("closed_interface", {}),
        "numerics.momentum.terms.surface_tension.closed_interface",
    )
    _require_value(
        closed_interface.get("endpoint"),
        "geometric_cell_fraction",
        "numerics.momentum.terms.surface_tension.closed_interface.endpoint",
    )
    residual_contract = _mapping(
        closed_interface.get("residual_contract", {}),
        "numerics.momentum.terms.surface_tension.closed_interface.residual_contract",
    )
    _require_value(
        residual_contract.get("metric"),
        "pressure_adjoint",
        "numerics.momentum.terms.surface_tension.closed_interface."
        "residual_contract.metric",
    )
    constraints = residual_contract.get("constraints")
    if constraints != ["cell_volume"]:
        raise ValueError(
            "numerics.momentum.terms.surface_tension.closed_interface."
            "residual_contract.constraints must be ['cell_volume']"
        )
    _require_true(
        residual_contract.get("fail_close", True),
        "numerics.momentum.terms.surface_tension.closed_interface."
        "residual_contract.fail_close",
    )

    projection = _mapping(numerics["projection"], "numerics.projection")
    poisson = _mapping(projection.get("poisson", {}), "numerics.projection.poisson")
    operator = _mapping(
        poisson.get("operator", {}),
        "numerics.projection.poisson.operator",
    )
    _require_value(
        operator.get("pressure_force_contract"),
        "variational_adjoint",
        "numerics.projection.poisson.operator.pressure_force_contract",
    )
    _require_value(
        operator.get("scalar_operator_pairing"),
        "variational_operator",
        "numerics.projection.poisson.operator.scalar_operator_pairing",
    )
    _require_value(
        operator.get("capillary_reaction_projection"),
        "pressure_component_hodge",
        "numerics.projection.poisson.operator.capillary_reaction_projection",
    )


def _validate_legacy_diffuse_stack(numerics: dict[str, Any]) -> None:
    transport = _optional_interface_transport(numerics)
    variable = str(transport.get("variable", "psi")).strip().lower()
    if variable in {"q", "theta"}:
        raise ValueError(
            f"numerics.interface.transport.variable={variable!r} requires "
            "interface.state_space.kind='geometric_cell_fraction'"
        )
    tracking = _optional_interface_tracking(numerics)
    primary = str(tracking.get("primary", "psi")).strip().lower()
    if primary in {"q", "theta"}:
        raise ValueError(
            f"numerics.interface.tracking.primary={primary!r} requires "
            "interface.state_space.kind='geometric_cell_fraction'"
        )


def _optional_interface_transport(numerics: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(numerics, dict):
        return {}
    interface_num = numerics.get("interface")
    if isinstance(interface_num, dict):
        transport = interface_num.get("transport", {})
        return transport if isinstance(transport, dict) else {}
    physical_time = numerics.get("physical_time", {})
    if isinstance(physical_time, dict):
        transport = physical_time.get("interface_advection", {})
        return transport if isinstance(transport, dict) else {}
    return {}


def _optional_interface_tracking(numerics: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(numerics, dict):
        return {}
    interface_num = numerics.get("interface")
    if isinstance(interface_num, dict):
        tracking = interface_num.get("tracking", {})
        return tracking if isinstance(tracking, dict) else {}
    return {}


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a mapping")
    return value


def _require_value(value: Any, expected: str, path: str) -> str:
    normalized = str(value).strip().lower()
    if normalized != expected:
        raise ValueError(f"{path} must be {expected!r}, got {value!r}")
    return normalized


def _require_true(value: Any, path: str) -> None:
    if value is not True:
        raise ValueError(f"{path} must be true")


def _positive_float(value: Any, path: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be a positive finite value") from exc
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise ValueError(f"{path} must be a positive finite value")
    return parsed


def _nonnegative_int(value: Any, path: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{path} must be a non-negative integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be a non-negative integer") from exc
    if parsed < 0:
        raise ValueError(f"{path} must be a non-negative integer")
    return parsed
