# CHK-RA-CH14-VAR-044 - Pressure/Velocity G2 Work-Closure Gate

Date: 2026-05-17

Scope: implement the third diagnostic-only pressure/velocity work gate after
the PhaseRegion force adapter decision.  This checkpoint checks scalar virtual
work closure in the same face mass metric used by G0/G1.  It does not expose a
runtime force, call projection, perform a micro-step, or run T/8.

## Equation -> Discretization -> Code

| Equation / invariant | Discretization | Code |
|---|---|---|
| `dE[T_h(u_f)] + <s_f,u_f>_M = 0` | fixed-stratum virtual work | `fixed_stratum_virtual_work_check(...)` |
| same work metric | reuse G0 scalar and PhaseRegion `M_f` | `PhaseRegionPressureVelocityG2Report` |
| pressure work visibility | scalar `<p_f,u_f>_M` from G0 | `pressure_velocity_work` |
| no force admission | diagnostic-only gate | `force_admissible=false` |

## Implementation

Extended `src/twophase/simulation/phase_region_work_gate.py` with:

```text
PhaseRegionPressureVelocityG2Report
build_phase_region_pressure_velocity_g2_report(...)
```

The helper requires valid G0 and G1 reports, then rechecks the capillary work
identity using the same fixed-stratum Riesz oracle:

```text
dE[T_h(u_f)] + <s_f,u_f>_M = 0
```

It also verifies that G0's `surface_velocity_work` is the same scalar as the
Riesz check's `capillary_power`.  This catches any later accidental change of
weights or face-space pairing.

## Tests

Extended `src/twophase/tests/test_phase_region_force_admission.py` with:

```text
fixed-stratum work closure PASS
mismatched G0 surface work rejected
velocity outside fixed stratum rejected
```

The passing test uses the already scaled fixed-stratum velocity attached by
`PhaseRegionForceDiagnostics`.  The failing fixed-stratum test intentionally
uses an oversized face velocity and a large finite-difference epsilon, so the
underlying stratum check fails closed before any projection is attempted.

## Validation

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
= PASS: 857 passed, 35 skipped
```

The current `make test` target ran the full suite despite the targeted
`PYTEST_ARGS`.

## Next Gate

G3 should be a zero-step explicit face-projection oracle:

```text
u_f^+ = u_f - dt p_f + dt s_f
```

using face arrays directly.  The existing nodal `force_components` route must
remain blocked for `s_f`.

[SOLID-X] Added a diagnostic G2 report and tests only; no production force
route, projection call, runtime adapter force exposure, YAML route, experiment
physical parameter, nonlinear optimizer implementation, GPU runtime path, CFL,
damping, smoothing, tolerance weakening, rebuild skipping, FD/WENO/PPE
fallback, hidden CPU fallback, micro-step, T/8 runtime run, main merge, branch
deletion, worktree removal, or origin push changed.
