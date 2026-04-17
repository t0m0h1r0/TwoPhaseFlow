# WIKI-T-038: xi-Space eps Definition for Non-Uniform CCD Grids

**Status**: Verified (exp11-35/36, exp11-22/33 updated)
**Related**: WIKI-T-031, WIKI-T-032, WIKI-T-035, WIKI-T-037

## Problem Statement

On interface-fitted non-uniform grids (alpha_grid > 1), the CCD metric
transform requires the grid density Gaussian `omega(phi)` to be adequately
resolved in xi-space (computational uniform space). The legacy definition

    eps_g = eps_g_factor * eps,   eps = eps_factor * h_uniform

results in a xi-space transition width of

    W_xi = eps_g / delta_x_min = eps_g_factor * eps_ratio * (h_uniform / delta_x_min)

where `delta_x_min = h_uniform / alpha` at the interface. This gives
`W_xi = eps_g_factor * eps_ratio` cells -- a **constant independent of N**.
With default `eps_g_factor=2, eps_ratio=0.5`, W_xi = 1 cell, making CCD
6th-order metric differentiation impossible (requires >= 4 cells).

## Solution: xi-Space Cell-Based Definition

### A. Grid density width (eps_g_cells)

Define `eps_g` as a fixed number of **uniform-grid cells**:

    eps_g = eps_g_cells * (L / N)   per axis

This ensures `W_xi = eps_g_cells` cells regardless of N or alpha. The
minimum requirement is `eps_g_cells >= 4` for CCD resolution.

Implementation: `GridConfig.eps_g_cells` -> `Grid.update_from_levelset()`
conditionally uses `eps_g_cells * L[ax]/N[ax]` instead of `eps_g_factor * eps`.

### B. Heaviside smoothing width (eps_xi_cells)

Define `eps(x) = eps_xi_cells * h_local(x)` as a spatially varying 2D field:

    eps_field = eps_xi_cells * max(h_x, h_y)

At the interface (fine cells): eps is small -> narrow transition.
Far from interface (coarse cells): eps is large -> wide transition.
In xi-space: always `eps_xi_cells` cells wide.

Implementation: `_make_eps_field()` in ns_pipeline and experiment scripts.
`heaviside()`, `invert_heaviside()` already support array eps via broadcasting.

## Key Design Decisions

1. **grid.update_from_levelset still takes scalar eps** for logit inversion --
   the Heaviside must be inverted with the same scale it was created with.

2. **Reinitializer receives `min(eps_field)` as scalar** -- conservative CFL
   bound for `compute_dtau`. DGR reinitializer is grid-agnostic.

3. **eps_g_cells uses L/N (not h_local)** because eps_g controls grid density
   *before* the grid is rebuilt -- using h_local would create a circular
   dependency.

## Experimental Validation

### Advection benchmarks (exp11-35/36)

**Zalesak disk** (N=128, eps_ratio=0.5, T=2pi):

| Case           | L2(psi) | L2(phi) | area_err |
|----------------|---------|---------|----------|
| uniform        | 8.00e-2 | 1.05e-2 | 3.2e-4   |
| legacy a=2     | 1.47e-1 | 1.15e-2 | 3.5e-2   |
| gc4 a=2        | 8.92e-2 | 1.05e-2 | 1.2e-2   |
| gc4+xc1.5 a=2  | 9.94e-2 | 2.31e-2 | 2.0e-2   |

**Single vortex** (N=128, eps_ratio=1.5, T=8):

| Case           | L2(psi) | L2(phi) | area_err |
|----------------|---------|---------|----------|
| uniform        | 1.75e-1 | 3.43e-2 | 7.2e-2   |
| legacy a=2     | 2.37e-1 | 3.86e-2 | 1.19e-1  |
| gc4 a=2        | 2.21e-1 | 3.75e-2 | 1.08e-1  |
| gc4+xc1.5 a=2  | 2.16e-1 | 3.22e-2 | 1.07e-1  |

### Key Findings

1. **eps_g_cells=4 consistently improves over legacy** for all metrics on
   both benchmarks. Zalesak: L2(psi) 40% improvement, area_err 3x.

2. **eps_xi_cells=1.5 effectiveness depends on eps_ratio**:
   - eps_ratio >= 1.5 (vortex): L2(phi) = 3.22e-2 **beats uniform** (3.43e-2)
   - eps_ratio = 0.5 (Zalesak): L2(phi) degrades to 2.31e-2 (from 1.05e-2)
   - Hypothesis: small eps_ratio gives too-narrow interface in fine cells,
     causing under-resolution of the Heaviside profile itself.

3. **Recommended defaults**: `eps_g_cells=4` for all non-uniform runs.
   `eps_xi_cells` only when `eps_ratio >= 1.5`.

### NS-level experiments

**exp11-29** (N=32, static droplet, 100 steps):
- Uniform: mass_err=6.35e-6, max|u|=1.01e-2
- Non-uniform a=2 (gc4): mass_err=6.74e-6, max|u|=7.80e-3 (parasitic current reduced)

**exp12-17** (static droplet, N=32/48/64):
- N=48 non-uniform: parasitic current 5.59e-3 vs uniform 4.36e-1 (78x reduction)
- N=64 non-uniform: Laplace error 3.52e-2 vs uniform blowup

**exp12-18** (local eps validation, N=48):
- Config C (local eps + eps_xi_cells=1.5): parasitic current 5.93e-1,
  mass_err 4.32e-4 -- worse than Config B (fixed eps), suggesting
  eps_xi_cells interacts poorly with CSF surface tension at low N.

## Implementation Files

| File | Change |
|------|--------|
| `src/twophase/config.py` | `eps_g_cells: Optional[float]` in GridConfig |
| `src/twophase/core/grid.py` | Conditional eps_g in `update_from_levelset` |
| `src/twophase/simulation/config_io.py` | YAML parse for eps_g_cells, eps_xi_cells |
| `src/twophase/simulation/ns_pipeline.py` | Constructor args, `_make_eps_field()` |
| `src/twophase/levelset/reinit_ops.py` | `compute_dtau` array eps support |
