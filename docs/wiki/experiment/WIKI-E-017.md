---
ref_id: WIKI-E-017
title: "NS Pipeline Per-Timestep Grid Rebuild Integration Test (Exp 11-29)"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: "experiment/ch11/exp11_29_ns_grid_rebuild.py"
    description: "Static droplet NS pipeline with per-timestep interface-fitted grid rebuild"
consumers:
  - domain: A
    usage: "Paper §11.2 non-uniform grid verification"
  - domain: E
    usage: "Regression baseline for §13 non-uniform grid experiments"
depends_on:
  - "[[WIKI-E-001]]"
  - "[[WIKI-E-003]]"
  - "[[WIKI-E-012]]"
  - "[[WIKI-T-031]]"
  - "[[WIKI-T-014]]"
  - "[[WIKI-T-030]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-11
updated_at: 2026-04-16
---

# NS Pipeline Per-Timestep Grid Rebuild (Exp 11-29)

First integration test of interface-fitted grid rebuild within the full NS 5-stage predictor-corrector (`TwoPhaseNSSolver.step()`). Previous experiments (exp11_4, exp11_22) tested grid rebuild only at the component level (CCD metrics, CLS advection). This experiment validates the complete pipeline: advection → reinit → grid rebuild → curvature → PPE → velocity correction.

## Setup

- Static liquid droplet: R=0.25, center=(0.5,0.5), wall BC
- N=32, ρ_l/ρ_g=10, σ=1.0, μ=0.05, dt=1e-3, 100 steps
- Two cases: uniform (α=1) vs interface-fitted (α=2)
- α=2: grid rebuilt every timestep via `grid.update_from_levelset(phi, eps, ccd)`
- Field remapping: linear interpolation (psi, u, v) + mass correction
- Reinitialization: DGR (Direct Geometric Reinitialization) for α>1

## Key Results

| Metric | α=1 (uniform) | α=2 (interface-fitted) |
|--------|---------------|----------------------|
| Mass error |ΔM|/M₀ | 2.3e-4 | 2.6e-4 |
| Parasitic max|u| | 1.1e-1 | 4.1e-2 |
| h_min | 0.0312 (fixed) | 0.0224 (dynamic) |

## Findings

1. **Mass conservation equivalent** between α=1 and α=2 (2.3e-4 vs 2.6e-4). The initial implementation used Split reinitialization (CN-ADI diffusion) which computed `h = L/N` (nominal uniform spacing) instead of the actual minimum cell spacing `min(grid.h[ax])`. This caused CFL violation on non-uniform grids, resulting in 23% mass loss. Switching to DGR reinitialization for α>1 (which has no CN diffusion dependency) resolved the issue entirely. See Bug Fix section below.

2. **Parasitic currents reduced ~3×** with α=2 (4.1e-2 vs 1.1e-1). DGR maintains the interface profile more accurately than Split reinit on non-uniform grids, contributing to parasitic current reduction. The CSF ε-mismatch mechanism [[WIKI-T-009]] remains weak at this moderate grid ratio (h_min/h_uniform ≈ 0.72).

3. **Grid tracks interface dynamically** — h_min varies each timestep in response to parasitic-current-induced interface displacement. Confirms `update_from_levelset` → metric update → CCD adaptation chain works within the NS loop.

## Bug Fix (CHK-130)

Root cause: `SplitReinitializer` and its shared ops used `h = L/N` (uniform spacing assumption) for CN-ADI diffusion coefficients and CFL time step. On non-uniform grids (α>1), the actual minimum cell spacing is smaller than `L/N`, causing CFL violation and catastrophic mass loss (23%).

Four code files fixed:

| File | Change |
|------|--------|
| `src/twophase/levelset/reinit_ops.py` | `compute_dtau`: use `min(grid.h[ax])` for dtau |
| `src/twophase/levelset/reinit_ops.py` | `build_cn_factors`: use `min(grid.h[axis])` for CN tridiagonal |
| `src/twophase/levelset/reinit_split.py` | `self._h`: use `min(grid.h[ax])` per axis |
| `src/twophase/simulation/ns_pipeline.py` | `reinit_method` param: auto-select DGR when α>1 |
| `src/twophase/levelset/curvature_filter.py` | `_h_sq`: property (recomputed from live grid state) |

The DGR fallback is the primary fix for production use: DGR performs geometric reinitialization (invert_heaviside → rescale → heaviside) without CN diffusion, making it inherently safe on non-uniform grids [[WIKI-T-030]].

## Architecture Notes

- **CCD solver NOT reconstructed** per step — `_apply_metric()` reads `grid.J[axis]` live, so in-place Grid mutation suffices. This is a key efficiency finding vs exp11_22 pattern which reconstructed CCDSolver.
- **PPEBuilder NOT reconstructed** — `build(rho)` reads `grid.coords` at call time.
- **Pressure NOT remapped** — recomputed from PPE each step (authoritative).
- **dt_max uses h_min** — capillary CFL uses actual minimum spacing for stability.

## Known Limitation

Fixed ε = 1.5·h_uniform causes CSF force to spread over ~ε/h_local cells near interface. At α=2 this is ~1.6 cells (acceptable). At α=4 it would be ~19 cells, causing 400× parasitic current amplification. Spatially varying ε(x) = 1.5·h_local(x) is the documented remedy (future work).

## Implementation

Grid rebuild integrated into `TwoPhaseNSSolver.step()` at:
```
Stage 1: Advect ψ + reinitialize (DGR for α>1)
Stage 1b: _rebuild_grid(psi, u, v)
Stage 2: Curvature + CSF
Stage 3: NS predictor
Stage 4: PPE
Stage 5: Velocity corrector
```

Config: `GridCfg.alpha_grid` (config_io.py) flows through `from_config()` → `GridConfig` → `Grid`.
`reinit_method` defaults to `None` → auto-selects `'dgr'` when `alpha_grid > 1.0`, `'split'` otherwise.
