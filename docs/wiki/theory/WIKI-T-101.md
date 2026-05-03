---
ref_id: WIKI-T-101
title: "CLS Transport Uses Projected Velocity, Never Predictor Velocity"
domain: theory
status: ACTIVE
superseded_by: null
tags: [time_integration, cls, projected_velocity, ppe, causality, mass_conservation]
sources:
  - path: paper/sections/07_time_integration.tex
    description: "Velocity--PPE consistency and CLS advection ordering"
  - path: paper/sections/11_full_algorithm.tex
    description: "Full one-step algorithm stage ordering"
depends_on:
  - "[[WIKI-T-085]]"
  - "[[WIKI-T-088]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# CLS Transport Uses Projected Velocity

## Knowledge Card

The velocity used to advect `psi` is the previous PPE-projected velocity `u^n`,
not the unprojected predictor velocity `u*`.  Momentum EXT2 history also uses
projected velocity history.

This is a causal contract:

```text
PPE history -> projected velocities -> CLS and predictor -> new PPE -> new velocity
```

Using `u*` for CLS advection imports predictor divergence residual into the
interface transport equation and breaks the PPE RHS consistency between interface
and momentum updates.

## Consequences

- `psi` mass drift from predictor divergence is an ordering bug.
- Momentum advection history must come from projected velocities.
- CLS update and momentum predictor must share the same causal velocity history.
- The new predictor velocity becomes admissible only after PPE projection.

## Paper-Derived Rule

If a velocity has not passed through the current projection, it is not allowed to
transport the interface.
