# WIKI-L-071 — Ch14 Pressure/Velocity G3 Face-Projection Oracle PASS

## Claim

The pressure/velocity work gate now has a diagnostic-only G3 oracle for the
explicit face-array projection identity:

```text
u_f^+ = u_f - dt p_f + dt s_f
```

## Contract

Use `build_phase_region_pressure_velocity_g3_report(...)` after valid G0, G1,
and G2 reports.

The helper:

```text
requires face-shaped u_f, p_f, s_f
calls apply_pressure_projection(u_faces, p_faces, s_faces, dt)
checks the algebraic identity residual
records weighted pressure/surface update norms
keeps force_admissible == false
does not return projected faces
```

Do not route `s_f` through nodal `force_components`.

## Evidence

Artifact:

```text
artifacts/A/ch14_pressure_velocity_g3_face_projection_oracle_CHK-RA-CH14-VAR-045.md
```

Validation:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
= PASS: 859 passed, 35 skipped
```

## Next

Wire G0--G3 metrics into the existing Chapter 14 dry-run diagnostic, still with
`force_admissible=false`.  Runtime force exposure, micro-step, and T/8 remain
blocked.
