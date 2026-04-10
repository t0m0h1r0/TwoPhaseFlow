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
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-11
---

# NS Pipeline Per-Timestep Grid Rebuild (Exp 11-29)

First integration test of interface-fitted grid rebuild within the full NS 5-stage predictor-corrector (`TwoPhaseNSSolver.step()`). Previous experiments (exp11_4, exp11_22) tested grid rebuild only at the component level (CCD metrics, CLS advection). This experiment validates the complete pipeline: advection → reinit → grid rebuild → curvature → PPE → velocity correction.

## Setup

- Static liquid droplet: R=0.25, center=(0.5,0.5), wall BC
- N=32, ρ_l/ρ_g=10, σ=1.0, μ=0.05, dt=1e-3, 100 steps
- Two cases: uniform (α=1) vs interface-fitted (α=2)
- α=2: grid rebuilt every timestep via `grid.update_from_levelset(phi, eps, ccd)`
- Field remapping: linear interpolation (psi, u, v) + mass correction

## Key Results

| Metric | α=1 (uniform) | α=2 (interface-fitted) |
|--------|---------------|----------------------|
| Mass error |ΔM|/M₀ | 2.3e-4 | 7.7e-5 |
| Parasitic max|u| | 1.1e-1 | 1.4e-1 |
| h_min | 0.0312 (fixed) | 0.0290 (dynamic) |

## Findings

1. **Mass conservation improved 3×** with α=2 — per-step mass correction during remapping outperforms uniform grid's accumulation of CLS advection error.

2. **Parasitic currents 1.2× larger** with α=2 — mild increase because h_min/h_uniform ≈ 0.93 at α=2, N=32. The CSF ε-mismatch mechanism [[WIKI-T-009]] is weak at this moderate grid ratio. At α=4 the ratio would be ~13× (documented in `docs/memo/grid_refinement_negative_result.md`).

3. **Grid tracks interface dynamically** — h_min varies each timestep (0.026→0.029) in response to parasitic-current-induced interface displacement. Confirms `update_from_levelset` → metric update → CCD adaptation chain works within the NS loop.

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
Stage 1: Advect ψ + reinitialize
Stage 1b: _rebuild_grid(psi, u, v)    ← NEW
Stage 2: Curvature + CSF
Stage 3: NS predictor
Stage 4: PPE
Stage 5: Velocity corrector
```

Config: `GridCfg.alpha_grid` (config_io.py) flows through `from_config()` → `GridConfig` → `Grid`.
