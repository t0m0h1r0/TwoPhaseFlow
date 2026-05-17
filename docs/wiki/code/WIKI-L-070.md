# WIKI-L-070 — Ch14 Pressure/Velocity G2 Work-Closure Gate PASS

## Claim

The pressure/velocity work gate now has a diagnostic-only G2 check for scalar
virtual-work closure:

```text
dE[T_h(u_f)] + <s_f,u_f>_M = 0
```

using the same face mass metric as G0/G1.

## Contract

Use `build_phase_region_pressure_velocity_g2_report(...)` after valid G0 and
G1 reports.

The helper checks:

```text
fixed-stratum virtual work is valid
finite-difference power residual is bounded
Riesz residual is bounded
G0 surface work equals the Riesz capillary power
pressure work is finite
force_admissible == false
```

The gate does not project velocity and does not expose a runtime force.

## Evidence

Artifact:

```text
artifacts/A/ch14_pressure_velocity_g2_work_closure_gate_CHK-RA-CH14-VAR-044.md
```

Validation:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
= PASS: 857 passed, 35 skipped
```

## Next

G3 should test a zero-step explicit face projection:

```text
u_f^+ = u_f - dt p_f + dt s_f
```

using face arrays directly.  Do not route `s_f` through nodal
`force_components`.
