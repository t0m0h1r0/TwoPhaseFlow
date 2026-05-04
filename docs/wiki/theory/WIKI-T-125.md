---
ref_id: WIKI-T-125
title: "IMEX-BDF2 Predictor Uses Projected History, Not Star Velocity"
domain: theory
status: ACTIVE
superseded_by: null
tags: [imex_bdf2, ext2, projection, velocity_history, ppe, time_order]
sources:
  - path: paper/sections/07_time_integration.tex
    description: "CLS velocity/PPE consistency and IMEX-BDF2 EXT2 predictor history"
depends_on:
  - "[[WIKI-T-101]]"
  - "[[WIKI-T-103]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Projected-History Predictor

## Knowledge Card

The NS convective EXT2 term is built from projected velocity history
`{u^n, u^{n-1}}`, not from the unprojected predictor velocity `u*`.  The same
causal ordering underlies CLS transport: `psi` is advected by the previous
PPE-projected field, while `u*` is only an intermediate state before the new
PPE projection.

Using `u*` as an advecting velocity imports divergence residual into transport
and creates a PPE right-hand-side mismatch.

## Consequences

- Predictor output is not an admissible transport velocity.
- EXT2 history arrays must store projected velocities.
- Debugging mass drift should check whether an unprojected velocity leaked into
  CLS or momentum advection.
- Time-order claims depend on preserving this causal sequence.

## Paper-Derived Rule

Build all explicit advection histories from PPE-projected velocities; reserve
`u*` for the pre-projection correction step only.
