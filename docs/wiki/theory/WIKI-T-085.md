---
ref_id: WIKI-T-085
title: "CLS A--F Staging: Three Responsibilities, Six Gates"
domain: theory
status: ACTIVE
superseded_by: null
tags: [cls, staging, mass_conservation, geometry, correction, operator_splitting]
sources:
  - path: paper/sections/05b_cls_stages.tex
    description: "CLS A--F staging and three-responsibility principle"
depends_on:
  - "[[WIKI-T-078]]"
  - "[[WIKI-T-079]]"
  - "[[WIKI-T-081]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# CLS A--F Staging

## Knowledge Card

The paper's CLS algorithm is not just a list of operations.  It is a six-gate
responsibility split:

```text
A: conservative psi advection
B: post-advection psi-space mass closure
C: psi-to-phi mapping
D: Ridge--Eikonal redistancing
E: phi-to-psi mapping and geometry evaluation
F: post-reinitialization phi-space mass closure
```

The deeper invariant is the three-way separation between mass conservation,
geometry evaluation, and mass correction.

## Consequences

- `psi` transport owns conservative mass flux.
- `phi`/SDF quality owns metric geometry after redistancing.
- Mass closure is allowed, but only in the correct space for the current stage.
- Applying nodal CCD directly to steep `psi` transport is a stage violation.
- Computing curvature from an unreinitialized profile is a geometry-stage
  violation.

## Paper-Derived Rule

When CLS fails, identify which A--F gate was crossed with the wrong field before
tuning numerical parameters.
