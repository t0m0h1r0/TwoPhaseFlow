# CHK-RA-CH14-VAR-043 - Pressure/Velocity G1 Pressure-Range Gate

Date: 2026-05-17

Scope: implement the second diagnostic-only pressure/velocity work gate after
the PhaseRegion force adapter decision.  This checkpoint checks pressure-range
compatibility under the same face metric as G0.  It does not expose a runtime
force, call projection, perform a micro-step, or run T/8.

## Equation -> Discretization -> Code

| Equation / invariant | Discretization | Code |
|---|---|---|
| pressure reaction range | `range(M_f^{-1}D_f^T)` | `weighted_hodge_decomposition(...)` |
| capillary cochain split | range + Hodge diagnostic only | `admission.cochain.surface_acceleration` |
| same metric | reuse PhaseRegion `M_f` | `admission.face_metric.face_weight_components` |
| no silent conversion | pressure range checked separately from surface Hodge | `PhaseRegionPressureVelocityG1Report` |

## Implementation

Extended `src/twophase/simulation/phase_region_work_gate.py` with:

```text
PhaseRegionPressureVelocityG1Report
build_phase_region_pressure_velocity_g1_report(...)
```

The helper requires a valid G0 report, then decomposes:

```text
pressure_face_components
surface_acceleration
```

using the same `div_op` and `M_f`.  It accepts the pressure input only when
the pressure Hodge norm is small; it records the surface Hodge norm but does
not project or modify the capillary cochain.

## Tests

Extended `src/twophase/tests/test_phase_region_force_admission.py` with:

```text
manufactured pressure range PASS
nonrange pressure faces rejected
surface Hodge diagnostic remains visible
force_admissible remains false
```

The manufactured pressure range is built as:

```text
c_f = M_f^{-1} D_f^T p
```

with the same dense diagnostic `D_f` and the same `M_f` used by the
PhaseRegion cochain.

## Validation

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
= PASS: 854 passed, 35 skipped
```

The current `make test` target ran the full suite despite the targeted
`PYTEST_ARGS`.

## Next Gate

G2 should check scalar work closure:

```text
dE[T_h(u_f)] + <s_f,u_f>_M = 0
```

and pressure work measurement with the same face arrays and weights.  Runtime
force exposure, micro-step, and T/8 remain blocked.

[SOLID-X] Added a diagnostic G1 report and tests only; no production force
route, projection call, runtime adapter force exposure, YAML route, experiment
physical parameter, nonlinear optimizer implementation, GPU runtime path, CFL,
damping, smoothing, tolerance weakening, rebuild skipping, FD/WENO/PPE
fallback, hidden CPU fallback, micro-step, T/8 runtime run, main merge, branch
deletion, worktree removal, or origin push changed.
