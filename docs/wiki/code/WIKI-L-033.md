---
ref_id: WIKI-L-033
title: "Clean Integration of Phase-Separated FCCD Projection Closure"
domain: code
status: ACTIVE
superseded_by: null
tags: [fccd, projection, ppe, clean_merge, phase_separated, tests]
compiled_by: Codex
compiled_at: "2026-04-25"
---

# Clean Integration of Phase-Separated FCCD Projection Closure

## Merge policy

The research worktree contained many useful PoCs, but the clean merge imported
only the minimal production closure:

1. FCCD projection divergence rows match the matrix-free PPE wall rows.
2. FCCD pressure fluxes accept the PPE coefficient policy.
3. Phase-separated PPE forwards `coefficient_scheme="phase_separated"` into
   the projection corrector.
4. Regression tests prove `projection D_f A_f G_f == PPE apply`.

No exploratory YAML proliferation, result directories, q-jump PoC modes, or
experimental predictor-assembly branch were merged.

## Production files

- `src/twophase/simulation/divergence_ops.py`
  - adds wall-control-volume `_face_flux_divergence`,
  - adds `coefficient_scheme` / `phase_threshold` to FCCD pressure fluxes,
  - resets cached node widths on `update_weights()`.
- `src/twophase/simulation/ns_step_services.py`
  - forwards phase-separated PPE coefficient policy into FCCD projection.
- `src/twophase/tests/test_ns_pipeline_fccd.py`
  - adds non-uniform wall-grid operator equality tests,
  - adds corrector forwarding test.

## Required regression tests

The clean patch is protected by:

- `test_fccd_projection_divergence_matches_ppe_operator_nonuniform_wall`
- `test_phase_separated_fccd_projection_matches_ppe_operator_nonuniform_wall`
- `test_phase_separated_corrector_forwards_projection_coefficient_scheme`

These tests encode the actual bug: PPE and projection must share the same
`D_f A_f G_f` operator and the same phase cut.

## Validation snapshot

Clean-main validation:

```text
pytest: 378 passed, 18 skipped, 2 xfailed
ch13 faceproj debug: reached T=0.05
```

## Engineering lesson

For future clean merges after exploratory CFD debugging:

1. do not cherry-pick broad PoC branches,
2. identify the smallest violated discrete identity,
3. port only the code needed to restore that identity,
4. add an operator-level regression test before adding experiment configs,
5. run one representative experiment only after the algebraic test passes.

This keeps the production branch auditable and prevents exploratory hypotheses
from becoming permanent API surface.
