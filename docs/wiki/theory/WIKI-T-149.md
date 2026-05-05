---
ref_id: WIKI-T-149
title: "Periodic CCD Uses Interior Rows Everywhere"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ccd, periodic_boundary, compact_difference, block_circulant, boundary_closure]
sources:
  - path: paper/sections/appendix_c2_2_ccd_periodic_bc.tex
    description: "Periodic CCD closure and warning against one-sided boundary rows"
  - path: paper/sections/04b_ccd_bc.tex
    description: "Nonperiodic CCD boundary closure context"
depends_on:
  - "[[WIKI-T-012]]"
  - "[[WIKI-T-054]]"
  - "[[WIKI-T-090]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Periodic CCD Closure

## Knowledge Card

Periodic CCD is not obtained by applying nonperiodic one-sided boundary rows at
the domain ends.  For a periodic field, every independent node is an interior
node with wraparound neighbors.  The compact matrix is block-circulant.

Using one-sided boundary formulas on a periodic problem injects an artificial
boundary defect into a problem that has no boundary there.

## Consequences

- Periodic verification should assemble wraparound interior rows for all
  independent nodes.
- Boundary-specific rows are for fixed-end or wall problems only.
- A tiny boundary derivative defect can be amplified by multistep explicit
  histories and misread as an advection stability problem.
- Whole-domain order claims for periodic tests are invalid if the closure used
  nonperiodic rows.

## Paper-Derived Rule

For periodic CCD, use the interior compact stencil everywhere with wrapped
indices and a block-circulant operator.
