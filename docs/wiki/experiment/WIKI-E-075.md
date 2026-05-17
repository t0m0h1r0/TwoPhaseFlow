---
ref_id: WIKI-E-075
title: "Ch14 PhaseRegion Runtime Force Dry-Run PASS"
domain: experiment
status: ACTIVE
tags: [ch14, phase_region, runtime, face_cochain, variational, no_t8]
sources:
  - path: artifacts/A/ch14_phase_region_runtime_force_dry_run_CHK-RA-CH14-VAR-033.md
    description: "Runtime force dry-run implementation and validation"
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
force_admissible               = 0.0
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

This authorizes only a zero-step runtime diagnostic.  It does not authorize a
production force adapter, pressure/velocity coupling, nonlinear optimization,
micro-stepping, or T/8.  The next gate is to design the production-adjacent
ownership boundary for `Omega_g`, runtime `phi` gauge synchronization, and
face-cochain consumption while keeping `force_admissible = false`.
