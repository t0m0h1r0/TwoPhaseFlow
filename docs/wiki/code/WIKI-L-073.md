# WIKI-L-073 - Ch14 Pressure/Velocity G5 Face-Force Projection Probe PASS

## Claim

The pressure/velocity gate now has an explicit zero-step consumer for the
G4-admitted PhaseRegion face force:

```text
u_f^+ = u_f - dt p_f + dt s_f
```

It returns projected face arrays only.  It does not reconstruct nodal velocity
or mutate runtime state.

## Contract

Use `build_phase_region_pressure_velocity_g5_report(...)` only after a valid
G4 report.

The helper:

```text
requires g4.force_admissible=true
requires face-shaped u_f, p_f, s_f, M_f
rejects nodal-shaped velocity input
calls apply_pressure_projection on face arrays
returns projected_face_components only on a valid identity residual
```

This keeps the face-force route separate from
`FCCDDivergenceOperator.project_faces(..., force_components=...)`, which still
expects nodal vectors and must not receive PhaseRegion `s_f`.

## Evidence

Artifact:

```text
artifacts/A/ch14_pressure_velocity_g5_face_force_projection_probe_CHK-RA-CH14-VAR-048.md
```

Validation:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
= PASS: 865 passed, 35 skipped

make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
= PASS: g5_valid=1, face_force_consumed=1, force_admissible=1
```

## Boundary

This authorizes only a zero-step face projection probe.  A runtime micro-step
or T/8 still requires a separate controlled single-step gate for velocity
reconstruction/update and diagnostics.
