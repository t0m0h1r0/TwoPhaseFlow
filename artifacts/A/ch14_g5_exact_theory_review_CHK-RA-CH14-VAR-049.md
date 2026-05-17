# CHK-RA-CH14-VAR-049 - G5 Exact-Theory Review Hardening

Date: 2026-05-17

Scope: review the G4/G5 face-force admission and projection probe implemented
in this session, then strengthen the tests and runtime metrics where the
theory contract was still too implicit.

## Review Finding

No production force path or nodal-force route was found.  The one weak point
was in G5:

```text
G4 exposes face_force_components = s_f
G5 consumes face_force_components
```

Before this checkpoint, G5 checked face shapes and the projection identity, but
did not independently verify that the consumed payload still matched G4's
admitted face-force norm.  A caller could construct a stale or mutated G4-like
object with the same shapes and still pass the algebraic projection identity.

## Fix

`build_phase_region_pressure_velocity_g5_report(...)` now checks:

```text
||s_f(consumed)||_M == g4.face_force_weighted_l2
```

with a fail-closed `face_force_consistency_residual`.

The test suite now also recomputes the G5 projected weighted norm from the
closed-form exact expression:

```text
u_f^+ = u_f - dt p_f + dt s_f
||u_f^+||_M = sqrt(sum_axis sum_faces M_f (u_f^+)^2)
```

and rejects a deliberately mutated G4 face payload.

## Validation

Remote tests:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
```

Result:

```text
866 passed, 35 skipped
```

Runtime dry-run:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

Key metrics:

```text
g5_valid                         = 1.000000000000e+00
face_force_consumed              = 1.000000000000e+00
face_force_consistency_residual  = 0.000000000000e+00
face_projection_identity_linf    = 2.081668171172e-17
face_projected_weighted_l2       = 1.279680161323e-02
force_admissible                 = 1.000000000000e+00
```

## Code Review

[SOLID-X] No C1 violation found.  The helper remains a pure diagnostic builder:
no I/O, no state mutation, no velocity reconstruction, and no production
projection route.  Experiment I/O remains in `experiment/ch14` through the
existing experiment toolkit.

## Theory Consistency

The G5 probe now checks both:

```text
same admitted force:   ||s_f(consumed)||_M == ||s_f(admitted)||_M
projection identity:   u_f^+ - u_f + dt p_f - dt s_f = 0
```

This is still zero-step and face-space only.  It does not authorize
micro-stepping or T/8.

[SOLID-X] G5 exact-theory guard/tests/dry-run metric only; no production
runtime force route, nodal force route, velocity reconstruction, state
mutation, YAML route, experiment physical parameter, solver algorithm,
nonlinear optimizer implementation, GPU runtime path, CFL, damping, smoothing,
tolerance weakening, rebuild skipping, FD/WENO/PPE fallback, hidden CPU
fallback, micro-step, T/8 runtime run, main merge, branch deletion, worktree
removal, or origin push changed.
