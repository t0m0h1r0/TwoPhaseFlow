---
ref_id: WIKI-T-135
title: "Nonuniform Geometry Data Is a Shared Source, Not Per-Operator Metadata"
domain: theory
status: ACTIVE
superseded_by: null
tags: [nonuniform_grid, metrics, geometry_data, ccd, ppe, curvature]
sources:
  - path: paper/sections/10b_ccd_extensions.tex
    description: "Shared non-uniform grid metrics for CCD/FCCD/HFE/Ridge-Eikonal/PPE/curvature/CFL"
depends_on:
  - "[[WIKI-T-094]]"
  - "[[WIKI-T-130]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Shared Nonuniform Geometry Data

## Knowledge Card

The non-uniform grid chapter treats geometry data as a common numerical source:

```text
J_x, J_y, metric derivatives, H_x, H_y
```

These are generated once and then consumed by CCD/FCCD, HFE, Ridge--Eikonal,
PPE, velocity correction, curvature, and CFL evaluation.  The paper explicitly
rejects a situation where the PPE uses high-order metrics while curvature,
viscosity, or pressure correction use lower-order or independently generated
metrics.

## Consequences

- Metric inconsistency is a cross-operator bug, not a local interpolation detail.
- Non-uniform-grid tests should compare which geometry arrays each operator
  consumes.
- Updating grid generation must be treated as updating all downstream
  operators.
- Face balance can fail even when each individual operator is formally high
  order.

## Paper-Derived Rule

Make non-uniform metric arrays a single shared geometric source of truth across
all operators that participate in force balance or transport.
