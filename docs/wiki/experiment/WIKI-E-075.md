---
ref_id: WIKI-E-075
title: "Ch14 PhaseRegion Runtime Force Dry-Run PASS"
domain: experiment
status: ACTIVE
tags: [ch14, phase_region, runtime, face_cochain, variational, no_t8]
sources:
  - path: artifacts/A/ch14_phase_region_runtime_force_dry_run_CHK-RA-CH14-VAR-033.md
    description: "Runtime force dry-run implementation and validation"
  - path: artifacts/A/ch14_phase_region_runtime_force_dry_run_gates_CHK-RA-CH14-VAR-046.md
    description: "Runtime force dry-run with G0-G3 pressure/velocity gate metrics"
  - path: artifacts/A/ch14_pressure_velocity_g4_face_force_admission_CHK-RA-CH14-VAR-047.md
    description: "Runtime dry-run with G4 face-force admission metrics"
  - path: artifacts/A/ch14_pressure_velocity_g5_face_force_projection_probe_CHK-RA-CH14-VAR-048.md
    description: "Runtime dry-run with G5 zero-step face-force projection probe metrics"
  - path: experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
    description: "Zero-step runtime force dry-run diagnostic"
depends_on:
  - "[[WIKI-E-072]]"
  - "[[WIKI-E-073]]"
  - "[[WIKI-E-074]]"
  - "[[WIKI-L-059]]"
consumers:
  - domain: experiment
    usage: "Use before any PhaseRegion runtime force adapter, pressure/velocity coupling, micro-step, or T/8 probe"
  - domain: code
    usage: "Use before promoting runtime PhaseRegion face cochains into production code"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Runtime Force Dry-Run PASS

## Knowledge Card

The Ch14 oscillating-droplet runtime initial state now has a zero-step
PhaseRegion force dry-run.  Runtime still owns liquid volume `q_l`; the
PhaseRegion diagnostic owns the gas complement:

```text
q_g = |C| - q_l
```

The dry-run builds runtime `psi = H(-phi)` from the same chart, uses nodal
density for the face mass metric, assembles the closed-interface Riesz face
cochain, and verifies fixed-stratum virtual work on the actual runtime
admission grid.

It now also records the pressure/velocity gate ladder:

```text
G0 face-space/boundary/metric
G1 pressure range under the same M_f
G2 scalar work closure
G3 explicit face-array projection identity
G4 face-force admission
G5 admitted face-force projection probe
```

The pressure input for these gates is the Hodge range component from the same
diagnostic decomposition.  This avoids connecting the PhaseRegion face cochain
to production PPE or the nodal `force_components` route.

G4 changes the dry-run's final `force_admissible` metric to `1`, but only for a
face-shaped payload:

```text
face_force_components = s_f
```

G5 consumes that payload only as a zero-step face-array probe and returns
projected face arrays; the runtime solver still does not update velocity or
state.

## Validation

Remote command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

Result: PASS.

```text
runtime_steps                  = 0.000000000000e+00
complement_used                = 1.000000000000e+00
gas_target_volume              = 3.224248620783e-04
compat_linf                    = 0.000000000000e+00
self_fd_power_residual         = 2.481405282624e-07
self_riesz_residual            = 0.000000000000e+00
probe_fd_power_residual        = 2.481363539023e-07
probe_riesz_residual           = 0.000000000000e+00
hodge_divergence_linf          = 1.083435563487e-09
reaction_residual_ratio        = 7.097851774750e-01
reaction_residual_divergence_linf = 2.313299773959e-09
force_admissible               = 1.000000000000e+00
```

Updated G0--G5 metrics:

```text
g0_valid                       = 1.000000000000e+00
g1_valid                       = 1.000000000000e+00
g2_valid                       = 1.000000000000e+00
g3_valid                       = 1.000000000000e+00
g4_valid                       = 1.000000000000e+00
g5_valid                       = 1.000000000000e+00
pressure_hodge_weighted_l2     = 1.216174229615e-14
work_closure_residual          = 2.481405282624e-07
projection_identity_linf       = 2.081668171172e-17
face_force_exposed             = 1.000000000000e+00
face_force_consumed            = 1.000000000000e+00
surface_update_consistency_residual = 0.000000000000e+00
face_force_component_linf      = 0.000000000000e+00
face_force_consistency_residual = 0.000000000000e+00
face_projection_identity_linf  = 2.081668171172e-17
force_admissible               = 1.0
```

Visualization:

```text
experiment/ch14/results/diagnose_phase_region_runtime_force_dry_run/phase_region_runtime_force_dry_run.pdf
```

## Failed Attempts Kept

The dry-run first failed when cell density was passed to the face metric; the
metric requires nodal density compatible with the face arrays.  It also failed
when the full self acceleration left the fixed stratum.  The accepted test
uses the runtime nodal `psi` density and scales the virtual displacement to
`2%` of the sign margin, preserving the same work tolerances.

## Boundary

This authorizes only a zero-step runtime diagnostic, a production-adjacent
face-force payload after G0--G4, and a zero-step G5 face projection probe.  It
does not authorize pressure/velocity runtime coupling, velocity
reconstruction/update, nonlinear optimization, micro-stepping, or T/8.  The
next gate is a controlled single-step probe that accepts projected face arrays
directly and does not use the nodal `force_components` route.
