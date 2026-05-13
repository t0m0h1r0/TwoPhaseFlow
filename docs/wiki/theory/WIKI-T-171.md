---
ref_id: WIKI-T-171
title: "GPU-Resident Interface-Fitted Grid Rebuild Theory"
domain: theory
status: ACTIVE
superseded_by: null
tags: [gpu, nonuniform_grid, grid_rebuild, interface_tracking, remap, metrics, ch14]
sources:
  - path: artifacts/A/ch14_gpu_grid_rebuild_theory_CHK-RA-CH14-AO-FASTVOL-053.md
    description: "Theory and implementation contract for GPU-resident fitted-grid updates"
depends_on:
  - "[[WIKI-X-050]]"
  - "[[WIKI-L-043]]"
  - "[[WIKI-T-096]]"
  - "[[WIKI-T-135]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-13
---

# GPU-Resident Fitted-Grid Rebuild

## Knowledge Card

Interface-fitted nonuniform grid rebuilds are part of the Chapter 14 discrete
problem.  They must not be disabled for performance.  The correct GPU route is
to port the tensor-product coordinate update, regular-stratum guard,
conservative remap, and metric epoch rebuild to device-resident arrays.

For each axis `a`, the fitted coordinate map is a monotone physical map

```text
x_a = chi_a(xi_a),      xi_i = i / N_a.
```

The monitor `omega_a(x)` defines the new coordinates by equidistribution:

```text
int_0^{x'_i} omega_a(s) ds = (i / N_a) int_0^{L_a} omega_a(s) ds.
```

The GPU implementation should compute this with fixed-size vector primitives:
device monitor construction, prefix sums, monotone inverse-CDF search, lower
cell-width projection, and a bounded device-side regular-stratum correction.
No dynamic host compaction or per-node scalar synchronization is part of the
mathematical contract.

## Required Theorems

1. **Monotone-coordinate theorem.**  If `omega_a > 0` and the lower-width
   projection enforces `Delta x_i >= f_a` with `N_a f_a < L_a`, then the
   rebuilt coordinate vector remains strictly monotone and length-preserving.
2. **Metric-epoch theorem.**  Once `x'` is accepted, every grid-dependent
   object belongs to one epoch: cell widths, node widths, `J=d xi/dx`,
   `dJ/dxi`, cell volumes, face measures, active supports, pressure history,
   and device caches.  Mixed epochs are invalid.
3. **Conservative-remap theorem.**  Cell cochains such as `q`, density, and
   conservative momentum must be remapped by tensor-product overlap weights,
   not by nodal interpolation, so that physical integrals are preserved up to
   the declared quadrature order.
4. **Regular-P1-stratum theorem.**  The P1 geometry maps `Q_h(phi)` and
   `S_h(phi)` are smooth only while the zero level set avoids grid nodes.
   Rebuild acceptance therefore requires a device-side certificate
   `min_node |phi'(x')| >= eta`, where `eta` is derived from grid scale and
   roundoff, not an arbitrary micro-offset.
5. **Batched-synchronization theorem.**  The only scalar transfer needed by the
   grid-rebuild kernel is an epoch summary such as min spacing, min stratum
   margin, conservation residuals, and status bits.  It must be transferred in
   one packet after the fixed device work finishes.

## Implementation Contract

- Keep the coordinate arrays mirrored on host only as metadata; kernels consume
  device coordinates from the metric epoch cache.
- Construct interface monitors from `phi=H^{-1}(psi)` on device.  Closure
  crossing contributions should use fixed-shape masks and reductions rather
  than `argwhere`.
- Compute equidistribution with device `cumsum` and monotone inverse lookup.
  If backend `searchsorted` synchronizes, replace it with a custom monotone
  inverse-CDF kernel.
- Apply the cell-width floor as a projection onto the simplex with lower
  bounds:

```text
Delta x_i^* = f + beta max(Delta x_i - f, 0),
beta = (L - N f) / sum_i max(Delta x_i - f, 0).
```

- Enforce the regular stratum by fixed bounded sweeps on device.  For each
  coordinate line, compute a line shift from violating nodes using level-set
  gradients and monotonicity/floor bounds, apply all line shifts, then transfer
  only the final certificate packet.
- Remap conserved quantities by overlap matrices; remap gauge-like diagnostic
  fields by interpolation only when they are not the conservation carrier.
- Invalidate and rebuild every grid-dependent solver cache at the same epoch:
  CCD factors/metrics, FCCD geometry, PPE operator caches, active geometry
  supports, pressure history, face states, and output coordinate metadata.

## Negative Knowledge

The following are not valid GPU optimizations:

- switching to a static or uniform grid;
- lowering rebuild frequency to hide cost;
- skipping the regular-stratum guard;
- replacing conservative remap with nodal interpolation for conserved cochains;
- adding arbitrary `1e-10` coordinate nudges;
- using host `argwhere`/`unique` to build dynamic support inside the hot path;
- keeping stale device coordinates after a host-side rebuild.

## Acceptance Tests

- CPU/GPU coordinate update equivalence for monitor-only and wall+interface
  monitor cases.
- `L != 1` nonuniform metric tests after a rebuild.
- Exact mass/conservative-momentum preservation across remap.
- Regular-stratum guard test where an interface initially lands on a node.
- No inner-loop D2H test for rebuild monitor, inverse-CDF, and guard.
- Short capillary-wave run showing nonuniform rebuilds remain enabled and GPU
  utilization is no longer limited by Python CPU saturation.
