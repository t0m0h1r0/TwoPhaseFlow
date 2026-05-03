---
ref_id: WIKI-T-092
title: "Shared Shear Stress tau_xy Is a First-Class Discrete Object"
domain: theory
status: ACTIVE
superseded_by: null
tags: [viscosity, shear_stress, tau_xy, energy, colocated_grid, symmetry]
sources:
  - path: paper/sections/06d_viscous_3layer.tex
    description: "Shared tau_xy construction and idealized viscous energy estimate"
depends_on:
  - "[[WIKI-T-080]]"
  - "[[WIKI-T-091]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Shared Shear Stress tau_xy

## Knowledge Card

The off-diagonal stress `tau_xy` is not an incidental intermediate.  It must be
constructed once on a single locus and shared by both the x- and y-momentum
equations.

Duplicating the same formula independently in two momentum equations can create
small numerical asymmetries.  Those asymmetries are precisely where the idealized
viscous energy estimate loses its sign discipline.

## Consequences

- `tau_xy` and `tau_yx` should reference the same array.
- Corner/staggered extensions must move `mu` to that stress locus by a low-order
  shared average.
- The energy estimate is exact only under ideal adjoint/boundary assumptions,
  but shared stress remains the design guard.
- Interface fallbacks should preserve one stress tensor, not two separately
  patched component equations.

## Paper-Derived Rule

Treat shear stress as stored geometry of the discrete operator, not as a formula
to be recomputed wherever it is needed.
