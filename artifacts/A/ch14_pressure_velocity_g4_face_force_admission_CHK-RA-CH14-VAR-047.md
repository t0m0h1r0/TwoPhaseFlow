# CHK-RA-CH14-VAR-047 - Pressure/Velocity G4 Face-Force Admission

Date: 2026-05-17

Scope: add the final production-adjacent admission decision after the validated
G0--G3 pressure/velocity gates.  This checkpoint exposes only the face-shaped
PhaseRegion capillary cochain.  It does not connect that cochain to runtime
projection, nodal `force_components`, a micro-step, or T/8.

## Implementation

Updated:

```text
src/twophase/simulation/phase_region_work_gate.py
src/twophase/tests/test_phase_region_force_admission.py
experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

The new G4 helper:

```text
build_phase_region_pressure_velocity_g4_report(...)
```

requires:

```text
valid blocked adapter decision
valid G0 face-space/boundary/metric gate
valid G1 pressure-range gate
valid G2 fixed-stratum work-closure gate
valid G3 explicit face-projection identity gate
```

If all gates pass, it returns:

```text
force_admissible = true
face_force_components = tuple(s_f_axis)
face_force_shapes = face shapes, not nodal shapes
```

The helper does not return projected faces and does not provide a nodal
`force_components` field.

## A3 Contract

| Equation / invariant | Discretization | Code |
|---|---|---|
| `s_f=-M_f^{-1}T_h^*dE_h` | PhaseRegion face acceleration cochain | `admission.cochain.surface_acceleration` |
| `u_f, p_f, s_f` share space | face-array shapes and same boundary face space | G0 report |
| `p_f in range(M_f^{-1}D_f^T)` | weighted Hodge range gate | G1 report |
| `dE[T_h(u_f)] + <s_f,u_f>_M = 0` | fixed-stratum virtual-work oracle | G2 report |
| `u_f^+=u_f-dt p_f+dt s_f` | explicit face-array identity | G3 report |
| exposed force remains a face object | no nodal conversion and no projection call | G4 report |

The extra G4 scalar check is:

```text
||dt s_f||_M == surface_update_weighted_l2 from G3
```

so the object being exposed is exactly the force used by the face-projection
oracle.

## Validation

Remote tests:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
```

Result:

```text
862 passed, 35 skipped
```

Runtime dry-run:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

Key metrics:

```text
g0_valid                              = 1.000000000000e+00
g1_valid                              = 1.000000000000e+00
g2_valid                              = 1.000000000000e+00
g3_valid                              = 1.000000000000e+00
g4_valid                              = 1.000000000000e+00
projection_identity_linf              = 2.081668171172e-17
face_force_exposed                    = 1.000000000000e+00
face_force_weighted_l2                = 2.731625086117e+01
surface_update_consistency_residual   = 0.000000000000e+00
force_admissible                      = 1.000000000000e+00
```

Outputs:

```text
experiment/ch14/results/diagnose_phase_region_runtime_force_dry_run/data.npz
experiment/ch14/results/diagnose_phase_region_runtime_force_dry_run/phase_region_runtime_force_dry_run.pdf
```

## Boundary

`force_admissible=true` here means the face cochain is admitted to the
production-adjacent diagnostic object.  It does not mean the runtime solver is
using the force.  The remaining blocked work is an explicit face-force
projection consumer or single-step probe that accepts `face_force_components`
directly without routing through nodal `force_components`.

[SOLID-X] G4 diagnostic admission helper/tests/dry-run metrics only; no
production force path, runtime projection coupling, nodal force route, YAML
route, experiment physical parameter, solver algorithm, nonlinear optimizer
implementation, GPU runtime path, CFL, damping, smoothing, tolerance
weakening, rebuild skipping, FD/WENO/PPE fallback, hidden CPU fallback,
micro-step, T/8 runtime run, main merge, branch deletion, worktree removal, or
origin push changed.
