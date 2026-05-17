# CHK-RA-CH14-VAR-045 - Pressure/Velocity G3 Face-Projection Oracle

Date: 2026-05-17

Scope: implement the fourth diagnostic-only pressure/velocity work gate after
the PhaseRegion force adapter decision.  This checkpoint checks an explicit
face-array projection oracle.  It does not expose a runtime force, perform a
micro-step, or run T/8.

## Equation -> Discretization -> Code

| Equation / invariant | Discretization | Code |
|---|---|---|
| `u_f^+ = u_f - dt p_f + dt s_f` | explicit face-array projection | `apply_pressure_projection(...)` |
| `s_f` is already a face cochain | no nodal `force_components` conversion | `PhaseRegionPressureVelocityG3Report` |
| projection identity | face-array algebra residual | `projection_identity_linf` |
| no force admission | diagnostic-only gate | `force_admissible=false` |

## Implementation

Extended `src/twophase/simulation/phase_region_work_gate.py` with:

```text
PhaseRegionPressureVelocityG3Report
build_phase_region_pressure_velocity_g3_report(...)
```

The helper requires valid G0/G1/G2 reports, then calls:

```text
apply_pressure_projection(u_faces, p_faces, s_faces, dt)
```

with `s_faces=admission.cochain.surface_acceleration`.  It records the
projected face shapes, the algebraic identity residual, and weighted update
norms.  It does not return the projected face arrays, so this remains an
oracle/report rather than a runtime force route.

## Tests

Extended `src/twophase/tests/test_phase_region_force_admission.py` with:

```text
explicit face projection oracle PASS
nodal pressure component input rejected
```

The rejection test proves G3 still requires face-shaped pressure arrays even
after G0/G1/G2 have passed for a valid pressure-range input.

## Validation

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
= PASS: 859 passed, 35 skipped
```

The current `make test` target ran the full suite despite the targeted
`PYTEST_ARGS`.

## Next Gate

The pressure/velocity diagnostic ladder G0--G3 now exists.  The next safe step
is to wire G0--G3 metrics into the existing Chapter 14 dry-run diagnostic while
keeping `force_admissible=false`, then run the dry-run with visualization or
saved metrics.  Runtime force exposure and T/8 remain blocked.

[SOLID-X] Added a diagnostic G3 report and tests only; no production force
route, runtime adapter force exposure, YAML route, experiment physical
parameter, nonlinear optimizer implementation, GPU runtime path, CFL, damping,
smoothing, tolerance weakening, rebuild skipping, FD/WENO/PPE fallback, hidden
CPU fallback, micro-step, T/8 runtime run, main merge, branch deletion,
worktree removal, or origin push changed.
