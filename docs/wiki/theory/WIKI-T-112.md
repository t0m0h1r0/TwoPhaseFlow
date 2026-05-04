---
ref_id: WIKI-T-112
title: "Ridge Seeds Cannot Be Promoted by Proximity Alone"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ridge_eikonal, fmm, seeds, zero_set, periodicity, symmetry, reinitialization]
sources:
  - path: paper/sections/03d_ridge_eikonal.tex
    description: "FMM reconstruction boundary set and warning against artificial ridge seeds"
  - path: paper/sections/05_reinitialization.tex
    description: "Periodic quotient closure and restriction of FMM Dirichlet seeds"
depends_on:
  - "[[WIKI-T-048]]"
  - "[[WIKI-T-081]]"
  - "[[WIKI-T-086]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# No Proximity Seed Promotion

## Knowledge Card

The paper explicitly forbids adding new FMM Dirichlet zero seeds merely because
a ridge-like feature is close to the old interface.  The boundary set of the
Eikonal problem is the mathematical problem being solved.  Changing it from
`Gamma` to `Gamma union Gamma_art` changes the reconstructed zero set.

This matters especially under periodic or reflection symmetry: artificial seed
promotion can simultaneously break zero-set preservation and the quotient-space
identifications that make the domain periodic.

## Consequences

- FMM seeds must come from actual zero crossings or explicitly constrained wall
  contact seeds.
- Ridge candidates are not automatically `phi=0` boundary conditions.
- Symmetry preservation is part of seed admissibility.
- A "near interface" heuristic solves a different Eikonal boundary-value
  problem.

## Paper-Derived Rule

Do not promote auxiliary ridge maxima to zero-set seeds unless the algorithm has
explicitly changed the interface boundary set and can justify that change.
