---
ref_id: WIKI-T-084
title: "Non-Uniform Ridge--Eikonal Metric Guardrails"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ridge_eikonal, nonuniform_grid, hessian, wall_contact, epsilon, fccd]
sources:
  - path: paper/sections/10d_ridge_eikonal_nonuniform.tex
    description: "Non-uniform Ridge--Eikonal evaluation path, wall closure, and epsilon-local warnings"
depends_on:
  - "[[WIKI-T-031]]"
  - "[[WIKI-T-032]]"
  - "[[WIKI-T-048]]"
  - "[[WIKI-T-081]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Non-Uniform Ridge--Eikonal Metric Guardrails

## Knowledge Card

Non-uniform Ridge--Eikonal reconstruction has three non-negotiable metric
guardrails:

```text
evaluate ridge Hessians in physical space,
seed Eikonal only from true zero/contact sets,
and keep epsilon_local as reconstruction geometry, not CSF width.
```

The paper explicitly rejects the route that computes a Hessian in computational
`xi` space and then transforms it, because thin interface bands make that path
numerically inconsistent.

## Consequences

- Non-uniform CCD Hessians must be evaluated directly in physical space.
- Wall mirror completion may help detect geometry, but must not invent Eikonal
  seed points.
- Contact-line seeds are physical boundary data and must remain pinned under
  mass correction.
- `epsilon_local` belongs to Ridge--Eikonal reconstruction/reinitialization; it
  is not permission to use a spatially variable CSF delta width.
- FCCD geometry and reinitialized signed distance must reference the same grid
  metric fields.

## Paper-Derived Rule

Do not treat non-uniform reconstruction knobs as free numerical damping knobs;
each one is tied to a specific metric contract.
