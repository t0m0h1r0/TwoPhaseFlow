---
ref_id: WIKI-T-037
title: "Grid Remap Interpolation Order Limit: Coarse-to-Fine Upsampling Bottleneck"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: "src/twophase/core/grid_remap.py"
    description: "CubicGridRemapper (4-point Lagrange) and LinearGridRemapper"
  - path: "experiment/ch11/exp11_22_zalesak_nonuniform.py"
    description: "Zalesak non-uniform benchmark: cubic vs linear remap comparison"
  - path: "experiment/ch11/exp11_33_single_vortex_nonuniform.py"
    description: "Single vortex non-uniform benchmark: cubic vs linear remap comparison"
consumers:
  - domain: E
    usage: "Explains why non-uniform grid area_err remains 94x worse than uniform"
  - domain: T
    usage: "Extends WIKI-T-035 error taxonomy with remap-specific component"
depends_on:
  - "[[WIKI-T-031]]"
  - "[[WIKI-T-035]]"
  - "[[WIKI-L-018]]"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-17
---

# Grid Remap Interpolation Order Limit

## Problem Statement

When a non-uniform grid is rebuilt to track a moving interface, field values
must be remapped from old grid nodes to new grid nodes.  Higher-order
interpolation (cubic O(h^4) vs linear O(h^2)) should reduce remap error.

**Experimental finding:** CubicGridRemapper gives **no improvement** over
LinearGridRemapper for Heaviside fields with eps/h <= 1.

| Remapper | exp11_22 area_err (alpha=2) | exp11_33 area_err (alpha=2) |
|----------|---------------------------|---------------------------|
| Linear   | 3.57e-02                  | ~same                     |
| Cubic    | 3.63e-02                  | ~same                     |
| Uniform  | 3.82e-04                  | ~same                     |

The 94x accuracy gap persists regardless of interpolation order.

## Root Cause: Coarse-to-Fine Upsampling

The error is not controlled by interpolation order but by **source grid
resolution at the new interface location**.

### Mechanism

With reinit_freq=20 and dt=0.45/N (N=128):

1. Interface moves ~9 cell spacings between grid rebuilds
2. Old grid was **coarse** where the interface now sits (alpha concentrates
   cells only near the *old* interface position)
3. New grid is fine at the current interface location

The remap must interpolate psi (a near-Heaviside step, 1-2 cells wide) from
old coarse-grid values. With only 2-3 source sample points spanning the
transition region, **both linear and cubic interpolation reduce to the same
few-point fit** of a step function.

### Mathematical Statement

For a Heaviside field psi = H_eps(phi) with interface width ~2*eps:

- Number of source nodes spanning the transition: n_src ~ 2*eps / h_coarse
- With eps/h_uniform = 0.5 and alpha=2: h_coarse ~ 2*h_uniform near former
  far-field region, so n_src ~ 1-2

Linear interpolation error: O(h_coarse^2 * |d^2 psi/dx^2|) ~ O(1/eps^2 * h_coarse^2)
Cubic interpolation error:  O(h_coarse^4 * |d^4 psi/dx^4|) ~ O(1/eps^4 * h_coarse^4)

Both are O(1) when h_coarse/eps ~ O(1), which is the case here.

### Why eps/h=1.5 reduces the gap

At eps/h=1.5, the interface spans ~3-4 cells even on the coarse part of the
grid, giving the interpolant more information. The 94x ratio drops to ~4x.
However, the wider interface degrades absolute accuracy for both uniform and
non-uniform grids.

## Implications

1. **Interpolation order is not the bottleneck** for adaptive grid methods
   with frequent rebuilds and sharp interfaces.

2. **The fundamental constraint** is that the new fine-grid region was coarse
   on the old grid. No polynomial interpolation can recover sub-grid information.

3. **Potential mitigations** (not yet tested):
   - Rebuild less often (only when interface displacement exceeds threshold)
   - Use a wider transition zone to ensure 4+ source points
   - Pre-refine old grid near predicted interface motion before rebuilding
   - Accept the degradation and use non-uniform grids only for eps/h >= 1.5

4. **CubicGridRemapper is still useful** for smooth fields (e.g., velocity,
   pressure remapping during grid rebuild in NS pipeline) where the source
   grid adequately resolves the field.

## Related

- [[WIKI-T-031]] — Non-uniform grid CLS corrections (filter, mass, remap)
- [[WIKI-T-035]] — 5-component error decomposition for non-uniform grids
- [[WIKI-L-018]] — GridRemapper API and strategy hierarchy
- [[WIKI-X-014]] — Stability map and recommended defaults
