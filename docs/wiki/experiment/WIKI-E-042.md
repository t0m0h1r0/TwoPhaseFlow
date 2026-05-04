---
ref_id: WIKI-E-042
title: "V10 Splits Mass Success from Shape Hard Limits"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter13, v10, cls, mass_correction, type_b, type_d, shape_error]
sources:
  - path: paper/sections/13e_nonuniform_ns.tex
    description: "V10-a/b two-axis verdicts for mass and shape"
  - path: paper/sections/13f_error_budget.tex
    description: "V10 mass/shape rows in the integrated accuracy table"
depends_on:
  - "[[WIKI-T-087]]"
  - "[[WIKI-E-040]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# V10 Mass vs Shape Axes

## Knowledge Card

V10 is deliberately split into two verdict axes.  The mass axis passes by
Type-B structural correction through Olsson--Kreiss mass correction.  The shape
axis is Type-D because fixed-grid CLS phase/threshold error, slot
under-resolution, and grid-scale folded filaments impose hard limits.

This separation prevents a mass-conservation success from being overread as
shape-reconstruction success.

## Consequences

- V10-a/b mass drift is the primary Type-B success axis.
- Zalesak slot shape error is a fixed-grid resolution/threshold limit.
- Single-vortex reversal shape error reflects Eulerian fixed-grid filament
  limits.
- Non-uniform moving-interface CLS remains a future verification gate.

## Paper-Derived Rule

For strong CLS deformation tests, report mass and shape as separate verdicts.
