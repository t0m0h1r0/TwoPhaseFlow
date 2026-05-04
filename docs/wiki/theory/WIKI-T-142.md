---
ref_id: WIKI-T-142
title: "HFE Is Direct Hermite Steady Extension, Not a Virtual-Time Solver"
domain: theory
status: ACTIVE
superseded_by: null
tags: [hfe, hermite_extension, pressure_jump, steady_extension, virtual_time]
sources:
  - path: paper/sections/09c_hfe.tex
    description: "HFE as a direct Hermite approximation to the steady extension PDE"
depends_on:
  - "[[WIKI-T-099]]"
  - "[[WIKI-T-131]]"
  - "[[WIKI-T-134]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Direct Hermite Extension

## Knowledge Card

HFE is not a pseudo-time extension solve.  It is a direct Hermite construction
that approximates the steady extension PDE so that one-sided smooth fields can
be sampled by high-order stencils near the interface.

The paper's distinction is:

```text
HFE                 : direct local Hermite extension
virtual-time solve  : iterative extension evolution
```

## Consequences

- HFE cost and failure modes should not be analyzed as if it were an iterative
  extension PDE solver.
- The purpose is stencil regularity near a jump, not time advancement of a new
  physical field.
- HFE is mandatory when the solved pressure variable carries a Young--Laplace
  jump, but unnecessary for smoothed-Heaviside one-PPE pressure.
- Extension quality belongs to the one-sided pressure/jump closure, not to the
  CLS transport integrator.

## Paper-Derived Rule

Treat HFE as a local high-order trace-extension primitive, not as a hidden
virtual-time algorithm.
