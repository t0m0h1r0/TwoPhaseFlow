# CHK-RA-CH14-VAR-042 - Pressure/Velocity G0 Face-Space Gate

Date: 2026-05-17

Scope: implement the first diagnostic-only pressure/velocity work gate after
the PhaseRegion force adapter decision.  This checkpoint checks face-space,
boundary, and metric compatibility only.  It does not expose a runtime force,
call projection, perform a micro-step, or run T/8.

## Equation -> Discretization -> Code

| Equation / invariant | Discretization | Code |
|---|---|---|
| `s_f=-M_f^{-1}T_h^*dE_h` | PhaseRegion capillary face acceleration cochain | `admission.cochain.surface_acceleration` |
| `M_f` | PhaseRegion face mass metric | `admission.face_metric.face_weight_components` |
| `u_f` | runtime FCCD face velocity | caller-supplied `runtime_face_velocity_components` |
| `p_f` | runtime pressure reaction faces | caller-supplied `pressure_face_components` |
| boundary face space | direct face boundary projection | `apply_direct_face_boundary_space(...)` |
| work pairings | weighted face dot products | `build_phase_region_pressure_velocity_g0_report(...)` |

## Implementation

Added `src/twophase/simulation/phase_region_work_gate.py`:

```text
PhaseRegionPressureVelocityG0Report
build_phase_region_pressure_velocity_g0_report(...)
```

The helper accepts only already-built face arrays:

```text
s_f from PhaseRegionForceAdmission
u_f from runtime face velocity
p_f from pressure face reaction
M_f from the PhaseRegion face metric
```

It checks:

```text
shape(s_f) == shape(u_f) == shape(p_f) == shape(M_f)
apply_direct_face_boundary_space(s_f) == s_f
M_f is positive
work scalars use exactly the supplied M_f weights
force_admissible remains false
```

This keeps the CHK-041 boundary intact: `s_f` is already a face cochain and is
not passed through `FCCDDivergenceOperator.project_faces(...,
force_components=...)`, whose force argument is currently nodal.

## Tests

Extended `src/twophase/tests/test_phase_region_force_admission.py` with:

```text
matching face-space and metric PASS
nonuniform metric faces PASS through CCD metric construction
nodal component route rejected
boundary face-space mismatch rejected
pressure face-shape mismatch rejected
```

The nonuniform test uses explicit nonuniform `grid.coords` and calls
`grid._build_metrics(ccd=ccd)`, preserving the existing project rule that
nonuniform metric construction must not use a low-order substitute.

## Validation

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
= PASS: 852 passed, 35 skipped
```

The current `make test` target ran the full suite despite the targeted
`PYTEST_ARGS`.

## Next Gate

G1 should prove pressure-range compatibility without converting the PhaseRegion
Hodge component into a pressure range.  Runtime force exposure, micro-step, and
T/8 remain blocked.

[SOLID-X] Added a diagnostic report module and tests only; no production force
route, projection call, runtime adapter force exposure, YAML route, experiment
physical parameter, nonlinear optimizer implementation, GPU runtime path, CFL,
damping, smoothing, tolerance weakening, rebuild skipping, FD/WENO/PPE
fallback, hidden CPU fallback, micro-step, T/8 runtime run, main merge, branch
deletion, worktree removal, or origin push changed.
