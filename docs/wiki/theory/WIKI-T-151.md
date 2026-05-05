---
ref_id: WIKI-T-151
title: "Axis-Selective Fitting Is a Metric Mask, Not a New Operator"
domain: theory
status: ACTIVE
superseded_by: null
tags: [nonuniform_grid, axis_selective, grid_fitting, metrics, affine_jump]
sources:
  - path: docs/memo/CHK-RA-GRID-AXIS-SELECT-001.md
    description: "Axis-selective interface-fitted grid design and gates"
depends_on:
  - "[[WIKI-T-094]]"
  - "[[WIKI-T-135]]"
  - "[[WIKI-T-137]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Axis-Selective Grid Fitting

## Knowledge Card

Axis-selective fitting chooses which coordinate maps are nonuniform.  It does
not introduce a new derivative family.  Inactive axes remain the uniform-grid
special case with constant metric, zero metric derivative, and uniform control
volume widths.

For capillary-wave graphs, this matters because the normal direction needs
interface resolution while the tangential wave direction can stay uniform.
Avoiding unnecessary tangential metric variation reduces pressure-jump and
projection coupling risk.

## Consequences

- The fitting mask is a metric-policy input, not an operator switch.
- Scheduled rebuilds must use the current tracked interface field in physical
  coordinates.
- The affine jump datum and shared PPE/corrector requirement are unchanged;
  only the local physical face distance changes.
- Acceptance should verify that inactive axes remain exactly uniform.

## Paper-Derived Rule

Use axis-selective fitting to localize nonuniform metrics to the physically
needed directions while preserving the existing CCD/FCCD metric contract.
