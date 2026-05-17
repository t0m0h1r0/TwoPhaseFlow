# WIKI-L-072 - Ch14 Pressure/Velocity G4 Face-Force Admission PASS

## Claim

The pressure/velocity work gate now has a G4 final admission helper that can
expose the PhaseRegion capillary force as a face cochain after G0--G3 pass.

```text
face_force_components = s_f
force_admissible = true
```

This is a production-adjacent diagnostic admission, not a runtime solver
connection.

## Contract

Use `build_phase_region_pressure_velocity_g4_report(...)` only after a valid
blocked adapter decision and valid G0, G1, G2, and G3 reports.

The helper:

```text
requires the adapter decision to still be blocked
requires G0--G3 to be valid
checks G3's surface update is exactly dt*s_f in the same M_f metric
returns only face_force_components
does not provide nodal force_components
does not return projected faces
```

The existing `FCCDDivergenceOperator.project_faces(..., force_components=...)`
route remains forbidden for `s_f`, because that route converts nodal vectors
with `face_fluxes(...)`.

## Evidence

Artifact:

```text
artifacts/A/ch14_pressure_velocity_g4_face_force_admission_CHK-RA-CH14-VAR-047.md
```

Validation:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
= PASS: 862 passed, 35 skipped

make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
= PASS: g4_valid=1, face_force_exposed=1, force_admissible=1
```

## Boundary

This authorizes a face-force payload for the next explicit face-force consumer
or single-step probe.  It still does not authorize pressure/velocity runtime
coupling, a micro-step, or T/8.
