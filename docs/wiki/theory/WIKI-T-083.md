---
ref_id: WIKI-T-083
title: "Same-Time Capillary Jump Closure in the PPE"
domain: theory
status: ACTIVE
superseded_by: null
tags: [surface_tension, pressure_jump, ppe, csf, time_integration, parasitic_current]
sources:
  - path: paper/sections/07_time_integration.tex
    description: "Jump-decomposed CSF and same-time coupling of curvature, pressure increment, and correction"
depends_on:
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-014]]"
  - "[[WIKI-T-080]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Same-Time Capillary Jump Closure

## Knowledge Card

The paper's standard surface-tension treatment is not an explicit CSF body force
inserted into the momentum predictor.  It is a jump-decomposed CSF closure: the
Young--Laplace jump is injected into the PPE right-hand side at the same updated
interface time.

The key time-level contract is that `psi^{n+1}`, `kappa_lg^{n+1}`,
`J_p^{n+1}`, the pressure increment, and the velocity correction all refer to
the same interface position.

## Consequences

- Predictor-stage surface-tension forcing is not the standard route.
- Curvature must come from the already updated `psi^{n+1}`.
- Pressure jump and velocity correction must be closed in the same PPE stage.
- Parasitic-current reduction depends on this time-level alignment, not only on
  spatial balanced-force placement.

## Paper-Derived Rule

If capillary forcing is split across inconsistent interface times, the scheme has
introduced an avoidable surface-tension splitting error.
