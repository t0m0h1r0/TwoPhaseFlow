---
ref_id: WIKI-X-050
title: "Theory-First Debug Priority: Nonuniform Metrics and Interface-Tracking Rebuilds"
domain: cross-domain
status: ACTIVE
tags: [rca, implementation_tests, nonuniform_grid, grid_rebuild, metrics, interface_tracking]
sources:
  - path: artifacts/A/ch14_nonuniform_ccd_xi_metric_rca_CHK-RA-CH14-AO-FASTVOL-044.md
    description: "Ch14 capillary RCA showing nonuniform CCD used physical L/N where computational dxi=1/N was required"
  - path: docs/wiki/theory/WIKI-T-094.md
    description: "Non-uniform metrics need a single geometric source of truth"
  - path: docs/wiki/theory/WIKI-T-096.md
    description: "Regridding requires conservative remap, history reset, and face rebuild"
  - path: docs/wiki/theory/WIKI-T-135.md
    description: "Nonuniform geometry data is a shared source, not per-operator metadata"
  - path: docs/wiki/cross-domain/WIKI-X-043.md
    description: "RCA artifacts falsify shortcuts before authorizing fixes"
depends_on:
  - "[[WIKI-T-094]]"
  - "[[WIKI-T-096]]"
  - "[[WIKI-T-135]]"
  - "[[WIKI-X-043]]"
consumers:
  - domain: code
    usage: "When theory-predicted behavior fails in implementation tests, inspect nonuniform metric and rebuild contracts before tuning"
  - domain: experiment
    usage: "Use uniform/static-grid controls to separate physics failure from coordinate/rebuild implementation defects"
  - domain: theory
    usage: "Treat coordinate-space and remap compatibility as theorem preconditions, not implementation details"
compiled_by: ResearchArchitect
compiled_at: 2026-05-13
---

# Theory-First Debug Priority

When an implementation test fails even though the algebraic or physical theory
predicts success, first suspect the contracts that move the theorem between
state spaces:

1. nonuniform grid support;
2. interface-tracking grid rebuild support.

Do this before changing physical parameters, CFL, damping, smoothing,
tolerances, fallback solvers, or visual postprocessing.

## Why These Come First

Nonuniform grids and interface-following rebuilds are not passive metadata.
They change the measure, face Hodge, pressure/divergence pairing, transport
cell volumes, history coordinates, and cache lifetime.  A theorem that is exact
on one discrete complex is no longer being tested if one operator reads
physical `x`, another reads computational `xi`, or a history/rebuild path keeps
old-grid cochains alive.

The ch14 capillary RCA is the canonical example.  The nonuniform CCD path was
solving the raw compact derivative with physical spacing `L/N`, then applying
the metric `J = dxi/dx`.  For a short domain `L=0.02`, this over-scaled the
first derivative by `1/L` and the second derivative by `1/L^2`.  The theory was
not wrong; the coordinate-space contract was.

## First Checks

Use this sequence for theory-first implementation debugging:

1. Run a uniform-grid control with the same solver policy and physical
   parameters.
2. Run a static-grid or no-rebuild control when the failing path uses
   interface tracking.
3. Add a manufactured `L != 1` metric test so hidden `L/N` versus `1/N`
   mistakes cannot pass by dimensional accident.
4. Compare pre/post-rebuild conservation ledgers for `q`, density, momentum,
   pressure history, face states, and geometry state.
5. Verify that all paired operators use the same measure and face locus:
   `D`, `G`, PPE, pressure history, transport flux, capillary/gravity Hodge,
   and diagnostics.
6. Check that grid-dependent caches are invalidated and rebuilt after coordinate
   changes.

Only after these checks pass should the RCA spend effort on timestep policy,
solver iteration count, or physical-model alternatives.

## Red Flags

Treat these as immediate signs that nonuniform/rebuild compatibility is the
likely root:

- The test passes on uniform grid but fails on an otherwise identical
  nonuniform route.
- The test fails only after the first grid rebuild or after pressure/velocity
  history becomes active.
- Error size scales like a domain length factor (`1/L`, `1/L^2`) rather than a
  physical nondimensional group.
- Residuals jump across a remap boundary even when physical fields remain
  bounded.
- A fix proposal weakens tolerances or lowers CFL before proving coordinate and
  rebuild identities.

## Negative Knowledge

Do not record these as fixes:

- micro-offsets in geometry;
- CFL shrinkage to hide metric over-scaling;
- damping, smoothing, curvature caps, or clipping;
- hidden uniform-grid fallback under a nonuniform YAML;
- extra PPE/PCG iterations when the paired operator or metric is wrong.

These may change symptoms, but they do not repair the theorem preconditions.
