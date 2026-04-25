---
ref_id: WIKI-L-034
title: "ch13 Rising Bubble Closure: Face Buoyancy Residual + FMM Redistancing"
domain: code
status: ACTIVE
superseded_by: null
tags: [ch13, rising_bubble, buoyancy, fccd, projection, ridge_eikonal, fmm]
compiled_by: Codex
compiled_at: "2026-04-25"
---

# ch13 Rising Bubble Closure: Face Buoyancy Residual + FMM Redistancing

## Decision

The clean production path for
`ch13_rising_bubble_water_air_alpha2_n128x256.yaml` uses the last stable
`worktree-researcharchitect-src-refactor-plan` settings:

- AB2 convection,
- Crank--Nicolson viscosity with `richardson_picard`,
- `buoyancy_faceresidual_stagesplit_transversefullband`,
- face-flux projection,
- canonical face state and face-native predictor state.

## Why it stabilises

The buoyancy force is split as

```text
rho' g = -grad(rho' Phi_g) + Phi_g grad(rho').
```

Only the residual part belongs in the explicit predictor. The hydrostatic
gradient must stay in pressure space. The implementation therefore constructs
the residual acceleration on projection-native faces and carries that face
state through the predictor/corrector stage rather than recomputing an
incompatible nodal approximation later.

## Reinitialisation constraint

Ridge--Eikonal redistancing remains tied to the non-uniform FMM solve for
`|grad(phi)| = 1`. A fixed-sweep GPU pseudo-time Eikonal kernel is not accepted
as production-equivalent unless it proves residual convergence and wall-grid
consistency. In ch13 it delayed the instability but did not pass the full
`t=0.5` run.

## Validation

Remote validation on 2026-04-25:

```text
make test
  559 passed, 3 skipped, 2 xfailed

make run EXP=experiment/ch13/run.py ARGS="ch13_rising_bubble_water_air_alpha2_n128x256"
  reached t=0.5000, step=140
  final KE=9.494e-04
  final kappa_max=3.528e+03
```

## Follow-up

The next GPU optimisation target is not an approximate redistancing shortcut.
It is either:

1. a GPU FMM with the same accepted-set non-uniform update, or
2. a residual-converged GPU fast-sweeping method with explicit boundary proof.

