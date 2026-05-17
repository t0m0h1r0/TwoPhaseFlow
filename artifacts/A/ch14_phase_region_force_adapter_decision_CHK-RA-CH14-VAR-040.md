# CHK-RA-CH14-VAR-040 - PhaseRegion Force Adapter Decision

Date: 2026-05-17

Scope: implement the zero-step blocked consumer decision designed in
`CHK-RA-CH14-VAR-039`.  This checkpoint does not connect capillary force to
pressure/velocity projection, nonlinear optimization, micro-stepping, or T/8.

## Implementation

Added:

```text
PhaseRegionForceAdapterDecision
build_phase_region_force_adapter_decision(...)
```

The decision helper consumes:

```text
PhaseRegionForceAdmission
PhaseRegionForceAdmissionReport
required_metric_keys
```

and returns only:

```text
valid / reason
metrics
force_admissible = false
force_components = None
withheld_force_reason = pressure_velocity_work_gate_missing
```

It never exposes `surface_acceleration` or any face cochain as a runtime force.

## A3 Mapping

| Equation / invariant | Discretization | Code |
|---|---|---|
| diagnostic report only | require `report.valid` | `_adapter_decision_validity` |
| zero-step only | report/admission `runtime_steps == 0` | `_adapter_decision_validity` |
| same face layout | report face shapes equal candidate face shapes | `_adapter_decision_validity` |
| no force acceptance | force payload withheld | `force_components=None` |
| no pressure theorem yet | explicit block reason | `pressure_velocity_work_gate_missing` |

## Tests

Added tests for:

```text
valid report -> valid decision with force withheld
invalid report -> invalid decision
face-shape mismatch -> invalid decision
missing required metric -> invalid decision
force_components is always None
force_admissible remains false
```

## Runtime Dry-Run Guard

`experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py` now builds a
decision after the admission report and fails if the decision is invalid.  The
experiment still saves/prints diagnostic metrics only; no force is passed to a
solver step.

## Validation

Remote command:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
```

Result:

```text
847 passed, 35 skipped
```

Runtime dry-run regression:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

Result: PASS.

```text
self_fd_power_residual  = 2.481405282624e-07
probe_fd_power_residual = 2.481363539023e-07
hodge_divergence_linf   = 1.083435563487e-09
force_admissible        = 0.0
```

## Code Review

[SOLID-X] no violation.  The helper is pure, scalar-report oriented, and does
not perform I/O, mutate runtime state, invoke PPE/velocity code, or expose a
force vector.

## Theory Consistency

The decision is deliberately conservative:

```text
valid diagnostic object != admissible runtime force
```

It preserves the PhaseRegion chain up to zero-step diagnostics and makes the
missing pressure/velocity work theorem explicit.  The next gate is a
pressure/velocity work-gate design, not a micro-step or T/8 run.
