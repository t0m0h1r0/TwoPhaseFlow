---
ref_id: WIKI-E-020
title: "Grid Rebuild Frequency Calibration: Interface Motion vs Stale-Grid Tradeoff"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: "experiment/ch13/results/exp13_01"
    description: "Capillary wave at freq=1, 20"
  - path: "experiment/ch13/results/exp13_02"
    description: "Rising bubble at freq=1, 5, 20"
consumers:
  - domain: A
    usage: "Paper §13 benchmark results and rebuild frequency table"
  - domain: E
    usage: "Guidance for future non-uniform grid experiments"
depends_on:
  - "[[WIKI-E-017]]"
  - "[[WIKI-E-018]]"
  - "[[WIKI-E-019]]"
  - "[[WIKI-T-032]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-11
---

# Grid Rebuild Frequency Calibration

When applying the non-uniform grid pipeline to long-time ch13 benchmarks (~20-30k steps), per-step rebuild (freq=1) exposed two problems:
1. Linear interpolation error accumulates linearly with rebuild count
2. Repeated u, v interpolation acts as numerical diffusion, damping bubble rise

Solution: `grid_rebuild_freq` parameter (default 1), calibrated per experiment based on interface motion characteristics.

## Calibration Results (α=2, use_local_eps=true)

| Experiment | Interface motion | freq=1 | freq=5 | freq=20 | α=1 baseline |
|------------|------------------|--------|--------|---------|--------------|
| exp13_01 capillary wave | Standing oscillation | |ΔV|=5.6% | — | **|ΔV|=1.74%** | |ΔV|=1.89% |
| exp13_02 rising bubble | Continuous rise Δy~0.17 | yc 0.5→0.79, v=0.046 | **yc 0.5→0.586, v=0.039** | yc 0.5→**0.077**→0.393 (BROKEN) | yc 0.5→0.672, v=0.160 |

## Key Finding: Interface Motion Determines Optimal freq

**Standing-wave interfaces** (capillary): Higher freq tolerates stale grid because the interface stays within the initial refined region. freq=20 reduces interpolation diffusion 20× and actually beats the uniform baseline.

**Moving interfaces** (rising bubble): Lower freq required. At freq=20, the bubble drifts out of the refined region between rebuilds (19 consecutive stale-grid steps), degrading curvature and reinit. Physics breaks down — yc falls to wall (0.077) before stabilizing at 0.393. At freq=5, stale periods are short enough to track the moving interface while still reducing interpolation by 5×.

## Design Rule

For non-uniform grid + per-K-step rebuild, choose K such that:
```
K · max|interface velocity| · dt  <<  ε_g  (refined region half-width)
```
For exp13_02 bubble with v_interface ~ 0.05, dt ~ 1e-4, ε_g ~ 0.02:
- K=5:  K·v·dt ~ 2.5e-5 (0.1% of ε_g)  ← OK
- K=20: K·v·dt ~ 1e-4 (0.5% of ε_g)    ← accumulates over many rebuilds → breakdown

## Tradeoffs

freq=1 (per-step):
- Pro: Grid always tracks interface exactly
- Con: Interpolation diffusion damps rise velocity 3.5× (0.160→0.046)
- Con: Mass error accumulates linearly to ~O(10⁻²) over 30k steps

freq=5:
- Pro: 5× less interpolation → mass error ~10× better than freq=1
- Pro: Rise velocity ~freq=1 (damping still present but mass fixed)
- Con: Rise velocity still 4× below uniform baseline

freq=20:
- Works only for standing-wave interfaces
- Breaks moving-interface physics

## Taylor Deformation: Out of Scope

Non-uniform grid does NOT fix the Taylor deformation benchmark. All 8 sweep cases still blow up at t<0.05 due to explicit viscous CFL at u_max=1.0 boundary condition. Fix requires Crank-Nicolson viscous integration (exp11_25 validated but not yet wired into TwoPhaseNSSolver). See WIKI-E-016 §13.3.

## Recommended Defaults

| Problem type | Recommended freq |
|--------------|------------------|
| Standing droplet / oscillation | 10-20 |
| Slowly drifting interface | 5-10 |
| Fast-moving interface | 1-5 |
| Short test (<1000 steps) | 1 (default) |

Adaptive rebuild (trigger on `max_interface_displacement > ε_g/4`) is a cleaner solution for production use. Documented as future work.
