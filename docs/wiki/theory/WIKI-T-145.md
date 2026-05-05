---
ref_id: WIKI-T-145
title: "Young-Laplace Sign Convention Is a Global Pressure-Jump Contract"
domain: theory
status: ACTIVE
superseded_by: null
tags: [young_laplace, pressure_jump, sign_convention, curvature, surface_tension]
sources:
  - path: paper/sections/02_governing.tex
    description: "Global phase, normal, curvature, and jump sign convention"
  - path: paper/sections/02b_surface_tension.tex
    description: "CSF and pressure-jump consistency"
  - path: paper/sections/09e_ppe_bc.tex
    description: "PPE boundary and interface jump usage"
depends_on:
  - "[[WIKI-X-003]]"
  - "[[WIKI-X-039]]"
  - "[[WIKI-T-097]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Young-Laplace Sign Contract

## Knowledge Card

The paper fixes the phase and sign convention once:

```text
phi < 0 : liquid
phi > 0 : gas
n_lg    : grad(phi) / |grad(phi)|, liquid -> gas
kappa_lg: div(n_lg)
j_gl    : p_gas - p_liquid = -sigma kappa_lg
```

For a circular liquid droplet of radius `R`, `kappa_lg = 1/R`, so
`j_gl = -sigma/R`.  The liquid pressure is higher than the gas pressure.

This is not local notation.  It is a global contract for CSF, GFM/HFE, affine
pressure jumps, diagnostics, and Young-Laplace verification.

## Consequences

- Any interface-stress API must state whether it expects `p_g - p_l` or
  `p_l - p_g`.
- Curvature sign tests should include the circular droplet sanity check.
- A visually plausible capillary result can still be wrong if the jump sign is
  reversed.
- Code paths that convert between CSF and sharp jump forms must preserve this
  orientation exactly.

## Paper-Derived Rule

Treat `j_gl = p_gas - p_liquid = -sigma kappa_lg` as the canonical
Young-Laplace jump throughout the solver and paper.
