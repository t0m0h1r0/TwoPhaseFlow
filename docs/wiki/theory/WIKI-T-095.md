---
ref_id: WIKI-T-095
title: "Non-Uniform FCCD Order Has a Face-Centrality Gate"
domain: theory
status: ACTIVE
superseded_by: null
tags: [fccd, nonuniform_grid, face_center, truncation_order, balanced_force]
sources:
  - path: paper/sections/10c_fccd_nonuniform.tex
    description: "Non-uniform FCCD truncation order, central-face gate, and BF impact"
depends_on:
  - "[[WIKI-T-080]]"
  - "[[WIKI-T-088]]"
  - "[[WIKI-T-094]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Non-Uniform FCCD Face-Centrality Gate

## Knowledge Card

Non-uniform FCCD does not have one universal face order.  General off-center
faces are `O(H^3)`, while central faces with `theta=1/2` cancel the third-order
term and recover `O(H^4)`.

This is why the interface-fitted grid family matters: it enforces central faces
near the interface where Balanced--Force cancellation is needed.

## Consequences

- `O(H^4)` FCCD claims require the face-centrality condition.
- Boundary helper faces, HFE nearest points, GFM crossings, and jump-correction
  faces can be special lower-order sets if they are off-center.
- Special faces should be separated from the `O(H^4)` verification set.
- Non-uniform BF closure still requires the same jump face data in PPE and
  velocity correction; metric order alone is insufficient.

## Paper-Derived Rule

Before citing non-uniform FCCD order, classify the face by `theta`, not just by
the stencil formula.
