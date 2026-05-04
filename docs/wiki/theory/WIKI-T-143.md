---
ref_id: WIKI-T-143
title: "Mixed Derivatives Use Sequential 1D CCD, Not a Separate 2D Stencil"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ccd, mixed_derivative, tensor_product, nonuniform_grid, smoothness]
sources:
  - path: paper/sections/10b_ccd_extensions.tex
    description: "Mixed derivative construction by sequential one-dimensional CCD applications"
depends_on:
  - "[[WIKI-T-117]]"
  - "[[WIKI-T-135]]"
  - "[[WIKI-T-136]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Sequential 1D Mixed Derivatives

## Knowledge Card

The nonuniform mixed derivative path is not a special 2D compact stencil.
It applies the one-dimensional CCD machinery sequentially along coordinate
directions and then relies on sufficient smoothness and consistent metrics to
preserve the intended order.

The operator reading is:

```text
apply 1D CCD in one coordinate
apply 1D CCD in the other coordinate
then map through shared nonuniform metrics
```

## Consequences

- Mixed-derivative accuracy inherits tensor-product smoothness requirements.
- A degraded mixed derivative can be caused by metric inconsistency, not only
  by the derivative stencil itself.
- The construction is compatible with the shared-geometry rule for nonuniform
  CCD/FCCD/HFE/PPE components.
- Verification should avoid interpreting mixed derivatives as evidence for an
  unimplemented standalone 2D compact operator.

## Paper-Derived Rule

Read mixed derivatives as sequential coordinate-direction CCD operations
under the shared nonuniform metric contract.
