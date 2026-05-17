# WIKI-L-068 — Ch14 Pressure/Velocity G0 Face-Space Gate PASS

## Claim

`PhaseRegion` capillary acceleration `s_f` can now be checked against runtime
pressure/velocity face spaces by a diagnostic-only G0 gate, while
`force_admissible` remains false.

## Contract

Use `src/twophase/simulation/phase_region_work_gate.py` before any
pressure/velocity force coupling:

```text
build_phase_region_pressure_velocity_g0_report(...)
```

The helper verifies:

```text
shape(s_f) == shape(u_f) == shape(p_f) == shape(M_f)
apply_direct_face_boundary_space(s_f) == s_f
M_f > 0
<s_f,u_f>_M and <p_f,u_f>_M use the same supplied face weights
force_admissible == false
```

It accepts face arrays only.  Do not pass `PhaseRegion` `s_f` through
`FCCDDivergenceOperator.project_faces(..., force_components=...)`, because that
path still treats `force_components` as nodal components and calls
`face_fluxes(...)`.

## Boundary and Nonuniform Findings

The gate includes explicit boundary-space rejection: an `s_f` that changes
under `apply_direct_face_boundary_space(...)` fails closed.

The nonuniform test constructs CCD metrics explicitly and then runs G0 with the
resulting face weights.  This preserves the project rule that nonuniform metric
construction must not fall back to a low-order substitute.

## Evidence

Artifact:

```text
artifacts/A/ch14_pressure_velocity_g0_face_space_gate_CHK-RA-CH14-VAR-042.md
```

Validation:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
= PASS: 852 passed, 35 skipped
```

## Next

G1 must prove pressure-range compatibility under the same face metric.  Runtime
force exposure, micro-step, and T/8 remain blocked.
