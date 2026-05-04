---
ref_id: WIKI-T-128
title: "Balanced Buoyancy Removes Hydrostatic Work Before Prediction"
domain: theory
status: ACTIVE
superseded_by: null
tags: [buoyancy, balanced_force, hydrostatic, predictor, rising_bubble, projection]
sources:
  - path: paper/sections/02_governing.tex
    description: "Pressure-robust decomposition of gravity into gradient and residual components"
  - path: paper/sections/07_time_integration.tex
    description: "Balanced-force buoyancy residual evaluation in the predictor"
depends_on:
  - "[[WIKI-T-066]]"
  - "[[WIKI-T-074]]"
  - "[[WIKI-T-125]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Balanced-Buoyancy Predictor

## Knowledge Card

The paper does not put the full gravity force into the predictor as a raw nodal
body force.  It splits buoyancy into a hydrostatic gradient part and an
interface-supported residual:

```text
gradient/hydrostatic component -> pressure/PPE space
non-gradient residual          -> predictor forcing on the shared operator
```

This avoids creating predictor divergence from a force that should be absorbed
by pressure in a hydrostatic state.

## Consequences

- Rising-bubble forcing is a projection-coupled operation, not just `+rho*g`.
- The residual should be constructed from the already-updated `psi^{n+1}` and
  `rho^{n+1}`.
- Hydrostatic cancellation belongs to the same balanced-force family as
  pressure/surface-tension cancellation.
- The buoyancy wave time scale remains a physical explicit constraint when
  gravity is significant.

## Paper-Derived Rule

Remove the hydrostatic gradient component before prediction; let only the
non-gradient buoyancy residual drive velocity.
