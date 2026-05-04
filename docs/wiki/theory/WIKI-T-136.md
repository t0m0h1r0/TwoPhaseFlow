---
ref_id: WIKI-T-136
title: "DCCD and UCCD6 Filtering Occur in Computational Space Before Metrics"
domain: theory
status: ACTIVE
superseded_by: null
tags: [nonuniform_grid, dccd, uccd6, computational_space, filtering, metrics]
sources:
  - path: paper/sections/10b_ccd_extensions.tex
    description: "Ordering of DCCD/UCCD stabilization in xi-space before metric conversion"
depends_on:
  - "[[WIKI-T-089]]"
  - "[[WIKI-T-119]]"
  - "[[WIKI-T-135]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# xi-Space Stabilization

## Knowledge Card

On non-uniform grids, DCCD filters and UCCD6 stabilization are applied in the
uniform computational coordinate `xi` before the metric conversion.  Directly
filtering in physical `x` space would make high-frequency damping depend on
local grid spacing and destroy the intended spectral meaning of the filter.

The correct order is:

```text
differentiate/stabilize in xi-space
then apply physical-space metrics
```

## Consequences

- Non-uniform filters are not obtained by reusing uniform-grid physical
  stencils with variable spacing.
- The filter's spectral interpretation belongs to computational space.
- Metric conversion after filtering is part of the operator definition.
- A damping parameter calibrated on uniform grids is not meaningful if applied
  after non-uniform metric distortion.

## Paper-Derived Rule

For DCCD/UCCD6 on stretched grids, preserve the uniform computational-space
filter first, then map the result to physical space.
