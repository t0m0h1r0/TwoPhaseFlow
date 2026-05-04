---
ref_id: WIKI-T-091
title: "Variable-Viscosity Stress Must Stay in Full Divergence Form"
domain: theory
status: ACTIVE
superseded_by: null
tags: [viscosity, full_stress, variable_mu, interface_jump, operator_assignment]
sources:
  - path: paper/sections/06d_viscous_3layer.tex
    description: "Three-layer viscous architecture and prohibition of direct mu Laplacian"
depends_on:
  - "[[WIKI-T-078]]"
  - "[[WIKI-T-079]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Variable-Viscosity Full-Stress Form

## Knowledge Card

For two-phase variable-viscosity flow, the viscous term is not `mu laplacian u`.
The correct object is the full stress divergence `div(2 mu D)`.  Replacing it by
`mu laplacian u` drops the cross contribution from `grad mu`, which is singular
at a viscosity jump.

The paper's Layer A/B/C architecture preserves this structure:

```text
Layer A: velocity gradients
Layer B: stress tensor assembly
Layer C: stress divergence
```

## Consequences

- `mu laplacian u` is valid only in bulk regions where `grad mu = 0`.
- Interface-normal velocity-gradient stencils must not cross viscosity kinks
  with CCD.
- Stress assembly must happen before divergence, not after scalar Laplacians.
- The high-order residual in viscous implicit/DC paths must consume the same
  full-stress operator, not a simplified Laplacian surrogate.

## Paper-Derived Rule

If viscosity varies across the interface, discretize stress first and diverge it
second.
