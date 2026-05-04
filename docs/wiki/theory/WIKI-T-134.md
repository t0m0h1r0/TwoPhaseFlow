---
ref_id: WIKI-T-134
title: "HFE Extension Normal Is an SDF Transport Direction, Not the Stress-Jump Normal"
domain: theory
status: ACTIVE
superseded_by: null
tags: [hfe, extension_pde, normal_direction, pressure_jump, sdf]
sources:
  - path: paper/sections/09c_hfe.tex
    description: "HFE extension PDE and distinction between SDF normal and Young-Laplace normal"
depends_on:
  - "[[WIKI-T-099]]"
  - "[[WIKI-T-131]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# HFE Normal Role Separation

## Knowledge Card

HFE uses the SDF normal as an extension direction for a field continuation
problem.  That normal is not playing the same role as the oriented
liquid-to-gas normal in the Young--Laplace pressure jump.

The extension PDE aims for a steady state with zero normal derivative:

```text
n_phi · grad q = 0
```

while the stress-jump normal orients the physical pressure discontinuity.

## Consequences

- Changing Young--Laplace sign conventions must not silently flip HFE extension
  source/target logic.
- HFE is a field-continuation operation, not a force-balance operation.
- The SDF quality determines the extension direction even when the pressure
  jump uses the same geometric interface.
- Documentation should keep `n_phi` and `n_lg` roles explicit.

## Paper-Derived Rule

Use the SDF normal to extend fields and the oriented interface normal to define
stress jumps; do not collapse these two normals into one semantic object.
