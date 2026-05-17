# CHK-RA-CH12-13-EXPAUD-001 — Chapters 12--13 Experiment Audit

## Scope

User request: read Chapters 1--11 and Section 14.2, then identify whether
Chapter 12--13 need new experiments, reruns, or deletion of stale
experiments/descriptions.  Work was performed on branch
`codex/ra-ch12-13-experiment-audit-20260517` in the dedicated worktree
`.claude/worktrees/codex-ra-ch12-13-experiment-audit-20260517`.

## Verdict

- No rerun is required for V1--V11.  The new Chapter 14 PhaseRegion graph and
  closed-chart evidence remains reduced-chart evidence with
  `force_admissible=0`, so it does not invalidate the existing wall-bounded
  pressure-jump/HFE verification contracts.
- One Chapter 13 experiment must be added: V12, a closed-interface volume
  admission gate.  It records the current `active_geometry_capillary` YAML
  boundary for Section 14.2 and prevents the old `sharp_phase_volume` /
  Ridge--Eikonal patch from being read as a current production setting.
- Section 14.2 had stale prose.  It described Ridge--Eikonal with
  `sharp_phase_volume` as the production setting, but the current YAML uses
  `active_geometry_capillary` plus `compatibility_projection`.
- No tested experiment script should be deleted.  The existing one-period
  oscillating-droplet production run remains useful negative evidence:
  it completed with finite fields but is not accepted because the closed
  interface volume invariant failed.

## New V12 Evidence

Command:

```text
make cycle EXP=experiment/ch13/exp_V12_closed_interface_volume_gate.py
```

Result:

```text
current_active_geometry: ok
sharp_volume_on_compatibility_projection: ValueError
ridge_eikonal_on_active_geometry: ValueError
grid_dv_sum = 4.000000000000e-04
periodic_unique_area = 4.000000000000e-04
relative_overcount = +0.000000e+00
prefix step 1:
  t = 2.652412244614e-05
  mass_rel = -1.080216e-01
  sharp_area_rel = -5.993794e-03
prefix step 2:
  RuntimeError: grid rebuild received projection-native face history but the
  active reprojector cannot reproject face cochains
one_period_production_admissible = 0
```

## Paper Changes

- Added `paper/sections/13e3_closed_interface_volume_gate.tex`.
- Updated `paper/sections/13_verification.tex` and
  `paper/sections/13f_error_budget.tex` from V1--V11 to V1--V12.
- Updated `paper/sections/12h_summary.tex` so the U-to-V bridge sends the
  closed-interface production volume boundary to V12.
- Updated `paper/sections/14b_oscillating_droplet.tex` so the production YAML
  description matches the current config and the old sharp-volume path is
  treated as a fail-closed negative control.

## Boundary

V12 is an admission gate, not a new accepted physical benchmark.  It does not
authorize pressure/velocity force consumption, does not change the production
solver, and does not merge into `main`.

## SOLID-X

Experiment script, paper, wiki, artifact, and ledger updates only.  No
`src/twophase/`, solver algorithm, physical parameter, CFL, damping, smoothing,
tolerance weakening, rebuild skipping, FD/WENO/PPE fallback, hidden CPU
fallback, main merge, branch deletion, worktree removal, or origin push changed.
