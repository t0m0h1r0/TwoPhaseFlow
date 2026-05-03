---
ref_id: WIKI-T-130
title: "Nonuniform Projection Requires a Face-Adjoint Gradient Pair"
domain: theory
status: ACTIVE
superseded_by: null
tags: [projection, nonuniform_grid, face_average, adjoint_pair, ppe, balanced_force]
sources:
  - path: paper/sections/08b_pressure.tex
    description: "Non-uniform face-average corrector and adjoint gradient/divergence pair"
  - path: paper/sections/09f_pressure_summary.tex
    description: "Non-uniform jump-corrected face gradient contract"
depends_on:
  - "[[WIKI-T-094]]"
  - "[[WIKI-T-098]]"
  - "[[WIKI-T-122]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Face-Adjoint Projection

## Knowledge Card

On non-uniform grids, using a nodal CCD gradient for velocity correction while
the PPE was assembled as an FVM face flux leaves a metric mismatch.  The paper
repairs this by moving correction and PPE assembly into the same face-flux
space:

```text
G_adj       : face-average pressure gradient
D_bf        : adjoint divergence paired to G_adj
G_Gamma_adj : jump-corrected version using the same local face distance H_f
```

The important object is the adjoint pair, not either operator in isolation.

## Consequences

- Non-uniform projection consistency requires the same face metric in PPE and
  velocity correction.
- Pressure-jump corrections must use the same physical face distance `H_f`.
- A high-order nodal gradient can be less faithful than a lower-order
  face-adjoint pair when the PPE lives in face-flux space.
- Balanced-force audits on stretched grids must include adjointness and metric
  sharing.

## Paper-Derived Rule

For non-uniform projection, define pressure correction through the face-adjoint
gradient/divergence pair that assembles the PPE, then apply jump corrections in
that same face space.
