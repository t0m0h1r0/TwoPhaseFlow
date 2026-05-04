---
ref_id: WIKI-T-096
title: "Regridding Requires Conservative Remap, History Reset, and Face Rebuild"
domain: theory
status: ACTIVE
superseded_by: null
tags: [regridding, ale, moving_grid, pressure_jump, history_reset, face_geometry]
sources:
  - path: paper/sections/10_grid.tex
    description: "Moving-grid conservative update, history reset, and pressure-jump face-geometry rebuild"
depends_on:
  - "[[WIKI-T-080]]"
  - "[[WIKI-T-094]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Regridding Requires Remap, Reset, and Rebuild

## Knowledge Card

Moving an interface-fitted grid is not equivalent to interpolating `psi` onto new
nodes.  Regridding introduces an effective mesh velocity, so the standard path
requires conservative remap, velocity reprojection, history reset, and fresh
reconstruction of pressure-jump face geometry.

Old pressure jumps, HFE extension context, IPC pressure increments, and face
geometry are not transported state variables.  They are regenerated from the
current interface and current grid.

## Consequences

- Without conservative remap, grid motion appears as a missing conservation-law
  term and can lower time accuracy.
- Pressure/history quantities must be reset or consistently rebuilt after
  regridding.
- Jump-face data must be recomputed from current `phi`, `psi`, and grid metrics.
- Main-stage PPE and velocity correction must share the rebuilt face data.
- Any path missing these gates is diagnostic/comparative, not the standard
  moving-grid closure.

## Paper-Derived Rule

Regridding is a state-transition operation with conservation and history
contracts; it is not a mesh-only cosmetic update.
