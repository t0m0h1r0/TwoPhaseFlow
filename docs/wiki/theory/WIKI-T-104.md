---
ref_id: WIKI-T-104
title: "One-Step Algorithm Freezes Geometry and Material State Before Projection"
domain: theory
status: ACTIVE
superseded_by: null
tags: [algorithm, ordering, geometry, material_properties, projection, interface]
sources:
  - path: paper/sections/11_full_algorithm.tex
    description: "Seven-stage full timestep and shared geometry/material state"
depends_on:
  - "[[WIKI-T-085]]"
  - "[[WIKI-T-093]]"
  - "[[WIKI-T-101]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# One-Step Geometry/Material Freeze

## Knowledge Card

The seven-stage algorithm first closes interface transport, reinitialization,
geometry, and material properties.  Only then do predictor, PPE, and correction
consume a single shared state:

```text
psi, phi, rho, mu, kappa_lg, and interface face data
```

`rho^{n+1}` and `mu^{n+1}` are not updated mid-step.  They are fixed after the
interface/material stage and used consistently through curvature, predictor,
PPE, and correction.

## Consequences

- Mid-step material refresh creates a different PDE than the one projected.
- Curvature, surface tension, pressure jump, PPE RHS, and correction must refer
  to the same interface geometry.
- One-fluid and phase-separated PPE paths share stages 1--4 and differ only in
  how stages 5--7 consume the face data.
- Algorithm order is part of the numerical method, not presentation order.

## Paper-Derived Rule

Freeze the interface-derived state before momentum projection; then make every
later stage consume that same frozen state.
