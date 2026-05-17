# CHK-RA-CH14-VAR-038 - PhaseRegion Force Admission Report

Date: 2026-05-17

Scope: add a candidate-focused zero-step report layer for
`PhaseRegionForceAdmission`.  This checkpoint does not connect the candidate
to pressure/velocity projection, nonlinear optimization, micro-stepping, or a
T/8 runtime path.

## Why This Gate Exists

`CHK-RA-CH14-VAR-037` attached self/probe work, weighted Hodge, and
component-reaction diagnostics to the same zero-step candidate.  The next
risk is letting later adapter code inspect the object ad hoc and accidentally
treat "diagnostics exist" as "force is consumable".

The new report makes the admission boundary explicit:

```text
candidate valid
+ diagnostics valid
+ required scalar metrics present
+ runtime_steps == 0
+ force_admissible == false
-> report.valid
```

Any missing condition fails closed with a reason string.

## Implementation

Added:

```text
PhaseRegionForceAdmissionReport
build_phase_region_force_admission_report(...)
```

The report preserves a structure-of-arrays boundary:

```text
metrics: flat scalar dict
face_component_shapes: ((nx, ny+1), (nx+1, ny))
bc_type / grid_alpha / min_dx / max_dx: metadata
```

It records `compat_linf` when the runtime snapshot provides it, checks a
caller-declared set of required metric keys, and keeps the candidate's
`force_admissible` bit visible.

## A3 Mapping

| Equation / invariant | Discretization | Code |
|---|---|---|
| zero-step only | `runtime_steps == 0` | `_report_validity` |
| no force acceptance | explicit status bit | `force_admissible=False` |
| fixed-stratum work gate | diagnostics payload must be valid | `diagnostics_valid` |
| runtime chart compatibility | scalar snapshot diagnostic | `compat_linf` |
| boundary/nonuniform identity | read current grid metadata | `bc_type`, `min_dx`, `max_dx` |
| vectorized face layout | no per-cell object graph | `face_component_shapes` |

## Tests

Added tests for:

```text
valid report exports zero-step contract metrics
required metric omissions fail closed
invalid grid spacing fails closed
wall/nonuniform grid metadata is reported even on invalid candidates
```

The wall/nonuniform metadata test intentionally uses a fail-closed runtime-step
candidate, so no force path or pressure/velocity consumer is introduced.

## Experiment Regression

`experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py` now builds a
report after diagnostics and fails if the report is invalid.  The printed
physics/work metrics remain unchanged.

## Validation

Remote command:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
```

Result:

```text
843 passed, 35 skipped
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

[SOLID-X] no violation.  The report is a small scalar contract boundary; it
does not do I/O, mutate runtime state, or consume the force.

## Theory Consistency

The report continues the PhaseRegion-primary interpretation:

```text
Omega_g/q owner map
runtime psi gauge
face metric and Riesz cochain
diagnostic work/Hodge/reaction checks
adapter-visible admission report
```

This is still diagnostic-only.  The next gate may design a zero-step adapter
consumer that reads the report, but pressure/velocity coupling, micro-stepping,
and T/8 remain forbidden.
