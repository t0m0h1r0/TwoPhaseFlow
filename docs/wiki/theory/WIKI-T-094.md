---
ref_id: WIKI-T-094
title: "Non-Uniform Metrics Need a Single Geometric Source of Truth"
domain: theory
status: ACTIVE
superseded_by: null
tags: [nonuniform_grid, metrics, ccd, fccd, hfe, pressure, curvature]
sources:
  - path: paper/sections/10b_ccd_extensions.tex
    description: "Common non-uniform metric data for CCD/FCCD/HFE/PPE/curvature/CFL"
  - path: paper/sections/10_grid.tex
    description: "Metric coefficient precision and coordinate-generation order limits"
depends_on:
  - "[[WIKI-T-084]]"
  - "[[WIKI-T-090]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Non-Uniform Metric SSoT

## Knowledge Card

On a non-uniform grid, the grid metrics are shared geometry, not private
coefficients of individual operators.  `J_x`, `J_y`, their computational
derivatives, face distances, and related metric fields must be generated once
and consumed consistently by CCD/FCCD, HFE, Ridge--Eikonal, PPE, velocity
correction, curvature, viscosity, and CFL evaluation.

The paper also separates two accuracy claims: CCD can differentiate the generated
coordinate array at high order, but the coordinate array itself may be limited by
the quadrature used to generate it.

## Consequences

- Do not let PPE use high-order metrics while curvature or viscosity uses
  low-order metrics.
- Low-order `J_x` estimates can degrade transformed second derivatives to first
  or second order.
- Metric derivative order and coordinate-generation quadrature order must be
  verified separately.
- Balance claims on non-uniform grids require shared geometry, not just
  high-order formulas.

## Paper-Derived Rule

Treat grid metrics as global discrete geometry with provenance, not as local
helper arrays.
