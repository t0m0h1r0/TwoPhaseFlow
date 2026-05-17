# WIKI-L-069 — Ch14 Pressure/Velocity G1 Pressure-Range Gate PASS

## Claim

The pressure/velocity work gate now has a diagnostic-only G1 check proving
that pressure faces can be recognized as `range(M_f^{-1}D_f^T)` under the same
face metric used by the PhaseRegion capillary cochain.

## Contract

Use `build_phase_region_pressure_velocity_g1_report(...)` after a valid G0
face-space report.

The helper decomposes pressure faces and the capillary surface cochain with the
same `D_f` and `M_f`:

```text
pressure_face_components = pressure range candidate
surface_acceleration = capillary cochain diagnostic
```

G1 accepts pressure only when its Hodge part is negligible.  The capillary
surface Hodge part is recorded but not converted into the pressure range.

## Evidence

Artifact:

```text
artifacts/A/ch14_pressure_velocity_g1_pressure_range_gate_CHK-RA-CH14-VAR-043.md
```

Validation:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
= PASS: 854 passed, 35 skipped
```

## Next

G2 must check scalar work closure in the same metric:

```text
dE[T_h(u_f)] + <s_f,u_f>_M = 0
```

Runtime force exposure, micro-step, and T/8 remain blocked.
