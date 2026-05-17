# CHK-RA-CH14-VAR-048 - Pressure/Velocity G5 Face-Force Projection Probe

Date: 2026-05-17

Scope: add the first explicit consumer of the G4-admitted face force.  This is
a zero-step probe: it consumes face arrays and returns projected face arrays,
but it does not reconstruct nodal velocity, mutate runtime state, perform a
micro-step, or run T/8.

## Implementation

Updated:

```text
src/twophase/simulation/phase_region_work_gate.py
src/twophase/tests/test_phase_region_force_admission.py
experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

The new helper:

```text
build_phase_region_pressure_velocity_g5_report(...)
```

requires a valid G4 report:

```text
g4.force_admissible = true
g4.face_force_components = s_f
```

It then checks face shapes for `u_f`, `p_f`, `s_f`, and `M_f`, applies:

```text
u_f^+ = u_f - dt p_f + dt s_f
```

and returns `projected_face_components` only if the identity residual is within
the projection tolerance.

## A3 Contract

| Equation / invariant | Discretization | Code |
|---|---|---|
| `s_f` is already face-shaped | G4-admitted face payload | `g4_report.face_force_components` |
| `u_f, p_f, s_f, M_f` share shapes | structure-of-arrays face components | G5 shape checks |
| `u_f^+=u_f-dt p_f+dt s_f` | explicit face projection | `apply_pressure_projection` |
| no nodal route | reject nodal-shaped velocity/pressure arrays | G5 fail-closed tests |
| no runtime mutation | return projected faces only | `PhaseRegionPressureVelocityG5Report` |

## Validation

Remote tests:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
```

Result:

```text
865 passed, 35 skipped
```

Runtime dry-run:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

Key metrics:

```text
g4_valid                         = 1.000000000000e+00
face_force_exposed               = 1.000000000000e+00
g5_valid                         = 1.000000000000e+00
face_force_consumed              = 1.000000000000e+00
face_projection_identity_linf    = 2.081668171172e-17
face_projected_weighted_l2       = 1.279680161323e-02
force_admissible                 = 1.000000000000e+00
```

Outputs:

```text
experiment/ch14/results/diagnose_phase_region_runtime_force_dry_run/data.npz
experiment/ch14/results/diagnose_phase_region_runtime_force_dry_run/phase_region_runtime_force_dry_run.pdf
```

## Boundary

This validates only the face-array consumer algebra.  The remaining gate before
any physical experiment is a controlled single-step probe that decides whether
and how to reconstruct/update runtime velocity from projected faces without
using nodal `force_components`, tolerance weakening, damping, smoothing, or CFL
retuning as a fix.

[SOLID-X] G5 zero-step face projection probe/tests/dry-run metrics only; no
production runtime force route, nodal force route, velocity reconstruction,
state mutation, YAML route, experiment physical parameter, solver algorithm,
nonlinear optimizer implementation, GPU runtime path, CFL, damping, smoothing,
tolerance weakening, rebuild skipping, FD/WENO/PPE fallback, hidden CPU
fallback, micro-step, T/8 runtime run, main merge, branch deletion, worktree
removal, or origin push changed.
