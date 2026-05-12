"""AO-Fast runtime contract adapters.

Symbol mapping
--------------
``q_C``:
    Physical liquid volume stored as the checkpoint array ``state/q``.
``theta_C``:
    Normalized liquid fraction stored as ``state/theta``.
``phi_i``:
    P1 gauge nodes stored as ``state/phi``.
``Gamma_h``:
    Fixed-stratum trace encoded by ``state/stratum/case_code``.

The adapters in this module validate the handoff that the geometric runtime
must satisfy before it can enter the Navier--Stokes pipeline.  Unsupported
active-projection/GPU cases fail closed here or at the runtime boundary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping


GEOMETRIC_CHECKPOINT_REQUIRED_ARRAYS = (
    "state/q",
    "state/theta",
    "state/phi",
    "state/stratum/case_code",
    "solver/transport_stage_ledger/epoch",
    "solver/compatibility_projection_ledger/epoch",
)
GEOMETRIC_FACE_HISTORY_PREFIXES = (
    "solver/p_prev_accel_face_components",
    "solver/projected_face_components",
)


class AOFastRuntimeDisabledError(ValueError):
    """Raised when a valid AO-Fast contract reaches the disabled runtime gate."""


@dataclass(frozen=True)
class AOFastRuntimeContract:
    """Parsed AO-Fast handoff, capillary, and checkpoint contract."""

    state_kind: str
    conserved_variable: str
    normalized_view: str
    gauge_variable: str
    tracking_method: str
    advection_scheme: str
    capillary_force_source: str
    capillary_endpoint: str
    capillary_constraints: tuple[str, ...]
    capillary_reaction_projection: str
    projection_implementation: str
    dense_reference: str
    gpu_required: bool
    fallback_policy: str
    active_projection_solver_scheme: str
    active_projection_primary: str
    active_projection_fallback_policy: str
    active_projection_fallback_target: str | None
    active_projection_fallback_triggers: tuple[str, ...]
    active_projection_convergence_norm: str
    active_projection_absolute_tolerance: float
    active_projection_relative_tolerance: float
    active_projection_max_iterations: int
    active_projection_pcg_tolerance: float
    active_projection_pcg_max_iterations: int
    active_projection_pcg_roundoff_floor: float | None
    active_projection_dc_tolerance: float
    active_projection_dc_max_iterations: int
    active_projection_dc_relaxation: float
    checkpoint_state_phase: str = "pre_step"
    checkpoint_required_arrays: tuple[str, ...] = GEOMETRIC_CHECKPOINT_REQUIRED_ARRAYS
    face_history_prefixes: tuple[str, ...] = GEOMETRIC_FACE_HISTORY_PREFIXES


@dataclass(frozen=True)
class AOFastCheckpointValidation:
    """Summary of a validated AO-Fast continuation checkpoint payload."""

    cell_shape: tuple[int, int]
    node_shape: tuple[int, int]
    required_arrays: tuple[str, ...]
    face_history_prefixes: tuple[str, ...]

    @property
    def grid_shape(self) -> tuple[int, int]:
        """Backward-compatible alias for the cell-cochain shape."""
        return self.cell_shape


def build_ao_fast_runtime_contract(cfg: Any) -> AOFastRuntimeContract:
    """Return the validated AO-Fast runtime contract for a parsed config."""
    state = getattr(cfg, "interface_state_space", None)
    run = getattr(cfg, "run", None)
    if getattr(state, "kind", "diffuse_cls") != "geometric_cell_fraction":
        raise ValueError("AO-Fast runtime contract requires geometric_cell_fraction")
    if run is None:
        raise ValueError("AO-Fast runtime contract requires cfg.run")

    _require(getattr(state, "conserved_variable", None), "q", "conserved_variable")
    _require(getattr(state, "normalized_view", None), "theta", "normalized_view")
    _require(getattr(state, "gauge_variable", None), "phi", "gauge_variable")
    _require(
        getattr(state, "projection_implementation", None),
        "active_cached",
        "projection_implementation",
    )
    _require(getattr(state, "dense_reference", None), "test_only", "dense_reference")
    if getattr(state, "gpu_required", False) is not True:
        raise ValueError("AO-Fast runtime contract requires gpu_required=True")
    fallback_policy = str(getattr(state, "fallback_policy", "none")).strip().lower()
    if fallback_policy not in {"none", "explicit_chain"}:
        raise ValueError(
            "AO-Fast runtime contract requires fallback_policy to be 'none' "
            "or 'explicit_chain'"
        )
    _validate_active_projection_solver_contract(state)
    _require(getattr(run, "interface_tracking_method", None), "q_cell_fraction",
             "interface_tracking_method")
    _require(getattr(run, "advection_scheme", None), "geometric_swept_volume",
             "advection_scheme")
    _require(getattr(run, "capillary_force_source", None), "bundle_virtual_work",
             "capillary_force_source")
    _require(getattr(run, "capillary_closed_interface_endpoint", None),
             "geometric_cell_fraction", "capillary_closed_interface_endpoint")
    constraints = tuple(getattr(run, "capillary_closed_interface_constraints", ()))
    if constraints != ("cell_volume",):
        raise ValueError(
            "AO-Fast capillary contract requires "
            "capillary_closed_interface_constraints=('cell_volume',)"
        )
    _require(getattr(run, "capillary_reaction_projection", None),
             "pressure_component_hodge", "capillary_reaction_projection")
    reinit_method = getattr(run, "reinit_method", None)
    reinit_every = int(getattr(run, "reinit_every", 0))
    if reinit_method not in {None, "compatibility_projection"}:
        raise ValueError(
            "AO-Fast runtime contract requires reinit_method=None or "
            "'compatibility_projection'"
        )
    if reinit_method is None and reinit_every != 0:
        raise ValueError("AO-Fast runtime contract requires reinit_every=0")
    if reinit_method == "compatibility_projection":
        raise ValueError(
            "AO-Fast active compatibility_projection runtime is not wired; "
            "use algorithm='none' with schedule.every_steps=0 until the fused "
            "active projection path is connected"
        )

    return AOFastRuntimeContract(
        state_kind="geometric_cell_fraction",
        conserved_variable="q",
        normalized_view="theta",
        gauge_variable="phi",
        tracking_method="q_cell_fraction",
        advection_scheme="geometric_swept_volume",
        capillary_force_source="bundle_virtual_work",
        capillary_endpoint="geometric_cell_fraction",
        capillary_constraints=("cell_volume",),
        capillary_reaction_projection="pressure_component_hodge",
        projection_implementation="active_cached",
        dense_reference="test_only",
        gpu_required=True,
        fallback_policy=fallback_policy,
        active_projection_solver_scheme=state.active_projection_solver_scheme,
        active_projection_primary=state.active_projection_primary,
        active_projection_fallback_policy=(
            state.active_projection_fallback_policy
        ),
        active_projection_fallback_target=state.active_projection_fallback_target,
        active_projection_fallback_triggers=(
            state.active_projection_fallback_triggers
        ),
        active_projection_convergence_norm=(
            state.active_projection_convergence_norm
        ),
        active_projection_absolute_tolerance=(
            state.active_projection_absolute_tolerance
        ),
        active_projection_relative_tolerance=(
            state.active_projection_relative_tolerance
        ),
        active_projection_max_iterations=state.active_projection_max_iterations,
        active_projection_pcg_tolerance=state.active_projection_pcg_tolerance,
        active_projection_pcg_max_iterations=(
            state.active_projection_pcg_max_iterations
        ),
        active_projection_pcg_roundoff_floor=(
            state.active_projection_pcg_roundoff_floor
        ),
        active_projection_dc_tolerance=state.active_projection_dc_tolerance,
        active_projection_dc_max_iterations=(
            state.active_projection_dc_max_iterations
        ),
        active_projection_dc_relaxation=state.active_projection_dc_relaxation,
    )


def raise_ao_fast_runtime_disabled(cfg: Any) -> None:
    """Validate AO-Fast handoff contracts, then fail closed before runtime."""
    contract = build_ao_fast_runtime_contract(cfg)
    raise AOFastRuntimeDisabledError(
        "geometric_cell_fraction solver runtime adapter is disabled until "
        "AO-Fast C10 gates pass; validated contract "
        f"transport={contract.advection_scheme}, "
        f"tracking={contract.tracking_method}, "
        f"capillary={contract.capillary_force_source}, "
        f"checkpoint_state_phase={contract.checkpoint_state_phase}"
    )


def validate_ao_fast_checkpoint_arrays(
    arrays: Mapping[str, Any],
    *,
    cell_shape: tuple[int, int] | None = None,
    node_shape: tuple[int, int] | None = None,
    grid_shape: tuple[int, int] | None = None,
) -> AOFastCheckpointValidation:
    """Validate test-only AO-Fast continuation checkpoint array contracts."""
    if cell_shape is None:
        if grid_shape is None:
            raise ValueError("AO-Fast checkpoint validation requires cell_shape")
        cell_shape = grid_shape
    elif grid_shape is not None and tuple(cell_shape) != tuple(grid_shape):
        raise ValueError("AO-Fast checkpoint cell_shape and grid_shape disagree")
    cell_shape = _validate_cell_shape(cell_shape)
    node_shape = _validate_node_shape(node_shape, cell_shape=cell_shape)
    for key in GEOMETRIC_CHECKPOINT_REQUIRED_ARRAYS:
        if key not in arrays:
            raise ValueError(f"AO-Fast checkpoint missing required array {key}")
    for key in ("state/q", "state/theta", "state/stratum/case_code"):
        shape = tuple(getattr(arrays[key], "shape", ()))
        if shape != cell_shape:
            raise ValueError(
                f"AO-Fast checkpoint array {key} shape {shape} "
                f"does not match cell_shape {cell_shape}"
            )
    phi_shape = tuple(getattr(arrays["state/phi"], "shape", ()))
    if phi_shape != node_shape:
        raise ValueError(
            f"AO-Fast checkpoint array state/phi shape {phi_shape} "
            f"does not match node_shape {node_shape}"
        )
    for prefix in GEOMETRIC_FACE_HISTORY_PREFIXES:
        _validate_face_history(
            arrays,
            prefix=prefix,
            cell_shape=cell_shape,
            node_shape=node_shape,
        )
    return AOFastCheckpointValidation(
        cell_shape=cell_shape,
        node_shape=node_shape,
        required_arrays=GEOMETRIC_CHECKPOINT_REQUIRED_ARRAYS,
        face_history_prefixes=GEOMETRIC_FACE_HISTORY_PREFIXES,
    )


def _validate_face_history(
    arrays: Mapping[str, Any],
    *,
    prefix: str,
    cell_shape: tuple[int, int],
    node_shape: tuple[int, int],
) -> None:
    count_key = f"{prefix}/count"
    if count_key not in arrays:
        raise ValueError(f"AO-Fast checkpoint missing face history {count_key}")
    count = int(arrays[count_key])
    if count != 2:
        raise ValueError(f"AO-Fast checkpoint {prefix} must contain 2 components")
    expected_shapes = (
        (cell_shape[0], node_shape[1]),
        (node_shape[0], cell_shape[1]),
    )
    for axis, expected_shape in enumerate(expected_shapes):
        key = f"{prefix}/{axis}"
        if key not in arrays:
            raise ValueError(f"AO-Fast checkpoint missing face history {key}")
        shape = tuple(getattr(arrays[key], "shape", ()))
        if shape != expected_shape:
            raise ValueError(
                f"AO-Fast checkpoint face history {key} shape {shape} "
                f"does not match {expected_shape}"
            )


def _validate_active_projection_solver_contract(state: Any) -> None:
    scheme = str(getattr(state, "active_projection_solver_scheme", "")).strip().lower()
    primary = str(getattr(state, "active_projection_primary", "")).strip().lower()
    fallback_policy = str(
        getattr(state, "active_projection_fallback_policy", "none")
    ).strip().lower()
    if str(getattr(state, "fallback_policy", "none")).strip().lower() != fallback_policy:
        raise ValueError(
            "AO-Fast runtime contract requires fallback_policy to match "
            "active_projection_fallback_policy"
        )
    if scheme == "pcg":
        _require(primary, "active_pcg_newton", "active_projection_primary")
        _require(fallback_policy, "none", "active_projection_fallback_policy")
        _require_empty_fallback(state)
    elif scheme == "dc":
        _require(primary, "residual_monotone_dc", "active_projection_primary")
        _require(fallback_policy, "none", "active_projection_fallback_policy")
        _require_empty_fallback(state)
    elif scheme == "dc_then_pcg":
        _require(primary, "residual_monotone_dc", "active_projection_primary")
        _require(
            fallback_policy,
            "explicit_chain",
            "active_projection_fallback_policy",
        )
        _require(
            getattr(state, "active_projection_fallback_target", None),
            "active_pcg_newton",
            "active_projection_fallback_target",
        )
        triggers = tuple(getattr(state, "active_projection_fallback_triggers", ()))
        if not triggers:
            raise ValueError(
                "AO-Fast runtime contract requires fallback triggers for "
                "dc_then_pcg"
            )
        _validate_fallback_triggers(triggers)
    else:
        raise ValueError(
            "AO-Fast runtime contract requires active_projection_solver_scheme "
            "to be 'pcg', 'dc', or 'dc_then_pcg'"
        )

    norm = str(getattr(state, "active_projection_convergence_norm", "")).strip().lower()
    _require(norm, "linf", "active_projection_convergence_norm")
    for name in (
        "active_projection_absolute_tolerance",
        "active_projection_pcg_tolerance",
        "active_projection_dc_tolerance",
        "active_projection_dc_relaxation",
    ):
        _require_positive_finite(getattr(state, name, None), name)
    _require_nonnegative_finite(
        getattr(state, "active_projection_relative_tolerance", None),
        "active_projection_relative_tolerance",
    )
    for name in (
        "active_projection_max_iterations",
        "active_projection_pcg_max_iterations",
        "active_projection_dc_max_iterations",
    ):
        _require_positive_int(getattr(state, name, None), name)
    floor = getattr(state, "active_projection_pcg_roundoff_floor", None)
    if floor is not None:
        _require_positive_finite(floor, "active_projection_pcg_roundoff_floor")
        if float(floor) > float(state.active_projection_pcg_tolerance):
            raise ValueError(
                "AO-Fast runtime contract requires "
                "active_projection_pcg_roundoff_floor <= "
                "active_projection_pcg_tolerance"
            )
    if float(state.active_projection_dc_relaxation) > 1.0:
        raise ValueError(
            "AO-Fast runtime contract requires "
            "active_projection_dc_relaxation <= 1.0"
        )


def _require_empty_fallback(state: Any) -> None:
    if getattr(state, "active_projection_fallback_target", None) is not None:
        raise ValueError(
            "AO-Fast runtime contract requires no fallback target for "
            "non-fallback active projection schemes"
        )
    if tuple(getattr(state, "active_projection_fallback_triggers", ())):
        raise ValueError(
            "AO-Fast runtime contract requires no fallback triggers for "
            "non-fallback active projection schemes"
        )


def _validate_fallback_triggers(triggers: tuple[Any, ...]) -> None:
    allowed = {
        "not_converged",
        "residual_floor_exceeded",
        "stagnation",
        "condition_gate_failed",
    }
    for trigger in triggers:
        if str(trigger).strip().lower() not in allowed:
            raise ValueError(
                "AO-Fast runtime contract requires admitted fallback triggers"
            )


def _validate_cell_shape(cell_shape: tuple[int, int]) -> tuple[int, int]:
    if len(cell_shape) != 2:
        raise ValueError("AO-Fast checkpoint validation currently supports 2D only")
    parsed = tuple(int(value) for value in cell_shape)
    if parsed[0] < 2 or parsed[1] < 2:
        raise ValueError("AO-Fast checkpoint cell_shape must be at least 2x2")
    return parsed


def _validate_node_shape(
    node_shape: tuple[int, int] | None,
    *,
    cell_shape: tuple[int, int],
) -> tuple[int, int]:
    expected = (cell_shape[0] + 1, cell_shape[1] + 1)
    if node_shape is None:
        return expected
    if len(node_shape) != 2:
        raise ValueError("AO-Fast checkpoint node_shape must be 2D")
    parsed = tuple(int(value) for value in node_shape)
    if parsed != expected:
        raise ValueError(
            f"AO-Fast checkpoint node_shape {parsed} must equal cell_shape+1 {expected}"
        )
    return parsed


def _require(value: Any, expected: str, name: str) -> None:
    if str(value).strip().lower() != expected:
        raise ValueError(f"AO-Fast runtime contract requires {name}={expected!r}")


def _require_positive_finite(value: Any, name: str) -> None:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"AO-Fast runtime contract requires {name} to be positive"
        ) from exc
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise ValueError(f"AO-Fast runtime contract requires {name} to be positive")


def _require_nonnegative_finite(value: Any, name: str) -> None:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"AO-Fast runtime contract requires {name} to be non-negative"
        ) from exc
    if not math.isfinite(parsed) or parsed < 0.0:
        raise ValueError(
            f"AO-Fast runtime contract requires {name} to be non-negative"
        )


def _require_positive_int(value: Any, name: str) -> None:
    if isinstance(value, bool):
        raise ValueError(
            f"AO-Fast runtime contract requires {name} to be a positive integer"
        )
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"AO-Fast runtime contract requires {name} to be a positive integer"
        ) from exc
    if parsed <= 0:
        raise ValueError(
            f"AO-Fast runtime contract requires {name} to be a positive integer"
        )
