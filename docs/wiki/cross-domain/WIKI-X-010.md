---
ref_id: WIKI-X-010
title: "Reinitializer Uniform-Grid Assumption: Verification Design Constraint"
domain: B
status: ACTIVE
superseded_by: null
sources:
  - path: "paper/sections/12g_nonuniform_grid.tex"
  - path: "experiment/ch12/exp12_17_static_droplet_nonuniform.py"
depends_on:
  - "[[WIKI-E-017]]"
  - "[[WIKI-E-018]]"
  - "[[WIKI-T-031]]"
compiled_by: ResearchArchitect
compiled_at: 2026-04-16
---

# Reinitializer Uniform-Grid Assumption: Verification Design Constraint

## Problem

The current reinitializer assumes uniform grid spacing. On non-uniform grids
(α=2 interface-adapted), a single reinitialization step without advection
produces mass shifts of 3e-2 to 2e-1. This is not a grid-adaptation defect
but a reinitializer limitation.

## Consequence for Verification Design

Any test comparing uniform vs non-uniform grids must simultaneously change
the reinitialization setting:
- Uniform (α=1): reinit every 2 steps (required for profile maintenance)
- Non-uniform (α=2): reinit off (forced by the implementation constraint)

This **confounds** two variables. Observed improvements in parasitic currents
and Laplace pressure accuracy on α=2 cannot be attributed to grid adaptation
alone — reinit-off removes a known error source.

## Required Control Experiment (Future Work)

To isolate the grid-adaptation effect:
- Run α=1 with reinit=off (same as α=2 condition)
- Compare α=1/reinit-off vs α=2/reinit-off

This separates the reinitializer effect from the grid-adaptation effect.

## Root Cause

The reinitializer's eikonal/diffusion PDE uses `dx` as a uniform scalar.
On non-uniform grids, the local spacing varies by up to 2x (α=2), causing
the characteristic thickness ε to be applied inconsistently across the
interface. Fix requires ξ-space reinitialization ([[WIKI-T-031]]).

## Cross-References

- [[WIKI-E-017]]: Grid-rebuild integration test (23% mass loss at α=2 with reinit)
- [[WIKI-E-018]]: Non-uniform grid NS convergence (reinit-off results)
- [[WIKI-T-031]]: Non-uniform grid CLS theory (ξ-space filter)
