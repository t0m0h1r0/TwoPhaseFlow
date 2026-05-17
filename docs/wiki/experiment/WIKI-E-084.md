---
ref_id: WIKI-E-084
title: "Ch14 Corrected YAML-Owned PhaseRegion Capillary One-Period PASS"
domain: experiment
status: ACTIVE
tags: [ch14, capillary_wave, phase_region, yaml_owned, cfl, visualization, one_period]
sources:
  - path: artifacts/A/ch14_capillary_yaml_time_owned_outputs_CHK-RA-CH14-VAR-063.md
    description: "Final corrected one-period run after YAML ownership review"
  - path: experiment/ch14/config/ch14_capillary.yaml
    description: "Canonical new-route Ch14 capillary configuration"
  - path: experiment/ch14/diagnose_phase_region_capillary_graph_steps.py
    description: "Reduced PhaseRegion graph runtime script"
depends_on:
  - "[[WIKI-E-083]]"
  - "[[WIKI-X-057]]"
  - "[[WIKI-T-178]]"
consumers:
  - domain: experiment
    usage: "Use as the current one-period Ch14 capillary graph evidence source"
  - domain: paper
    usage: "Use before citing Chapter 14.2 metrics or figures"
  - domain: code
    usage: "Use before changing YAML parsing, snapshot selection, or output fields"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Corrected YAML-Owned PhaseRegion Capillary One-Period PASS

## Claim

The current Ch14 capillary one-period evidence is the corrected
YAML-owned PhaseRegion graph route.  This card supersedes WIKI-E-083 as the
current paper-facing source because WIKI-E-083 predates the later user review
that restored physical-time snapshots, `cfl=1.0`, `interface`, `numerics`, and
the required `phi`/velocity/pressure outputs.

## Command

Before rerun, local and remote Ch14 result directories were deleted.  The
accepted run command was:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml'
```

The old production-style directory was verified absent:

```text
experiment/ch14/results/ch14_capillary
```

## YAML Contract

The canonical config owns:

```text
run.time.final = 0.046742983863
run.time.cfl   = 1.0
run.time.dt    = absent
output.snapshots.times =
  [0, T/4, T/2, 3T/4, T]
```

It also owns `interface`, `numerics`, scalar diagnostics, and snapshot figures
for `phi`, velocity, and pressure.

## Result

```text
steps                 = 3103
dt                    = 1.506380401644e-05
t_final               = 4.674298386300e-02
t_over_T              = 9.999999999959e-01
max_amplitude_error   = 1.644990574895e-10
max_velocity_error    = 3.033187518861e-08
max_energy_drift      = 1.025028838090e-06
max_residual_l2       = 0
max_volume_drift      = 5.421010862428e-20
max_step_wall_seconds = 3.863535495475e-02
target_met            = 1
force_admissible      = 0
```

Snapshot audit:

```text
snapshot_times   = [0.0, 0.01168951, 0.02337902, 0.03505347, 0.04674298]
snapshot_indices = [0, 776, 1552, 2327, 3103]
phi/u/v/pressure/rho snapshots = (5, 33, 33)
q_l/q_g snapshots              = (5, 32, 32)
```

## Interpretation

This validates the reduced graph-chart PhaseRegion route against the exact
linear capillary-wave reference for one period.  It also validates the YAML
output contract used by Chapter 14 figures.  It does not validate production
Navier--Stokes force coupling; the run remains explicitly diagnostic with
`force_admissible=0`.
