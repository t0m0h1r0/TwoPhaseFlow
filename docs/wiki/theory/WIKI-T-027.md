---
ref_id: WIKI-T-027
title: "CLS Reinitialization Mass Conservation: Problem Analysis and Proposed Fix"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: docs/memo/cls_reinit_mass_conservation.md
    git_hash: null
    description: "Full investigation memo with experimental data and design comparison"
  - path: src/twophase/levelset/reinitialize.py
    git_hash: null
    description: "Current Reinitializer implementation (no mass correction)"
consumers:
  - domain: L
    description: "reinitialize.py — implementation target"
  - domain: E
    description: "exp11_6 — single vortex mass error validation"
depends_on:
  - "[[WIKI-T-007]]: CLS transport and reinitialization theory"
  - "[[WIKI-E-003]]: LS transport experiments (exp11_6 single vortex)"
tags: [CLS, reinitialization, mass-conservation, quality-improvement]
---

## Problem

The CLS reinitialization PDE is conservative in continuous form (both compression and diffusion terms are in divergence form). However, the current discrete implementation loses mass due to:

1. **Discretization error** in CCD divergence (divergence theorem satisfied only to O(h^6))
2. **`clip(q, 0, 1)`** after each pseudo-time step destroys conservation
3. **Boundary flux** at walls not perfectly cancelled

Experimental evidence (single vortex, N=64): increasing reinit frequency from every-10-steps to every-step worsens mass error by **22x** (1.78e-3 to 3.85e-2), confirming reinitialization as the dominant mass loss mechanism.

## Proposed Fix: Interface-Weighted Mass Correction

After all `n_steps` pseudo-time iterations, apply:

```
delta_M = M_old - M_new
w = 4 * psi * (1 - psi)     # peaks at interface (psi=0.5), zero at bulk
psi += (delta_M / sum(w)) * w
```

This is a post-hoc approximation of the Lagrange multiplier method in Olsson & Kreiss (2005), using the same basis function f(psi) = 4*psi*(1-psi).

**Advantage over global scaling** (`psi *= M_old/M_new`): correction is concentrated at the interface, avoiding interface smearing in bulk regions.

## Implementation (2026-04-09)

Applied to both advection (`DissipativeCCDAdvection.advance()`, opt-in via `mass_correction=True`) and reinitialization (`Reinitializer.reinitialize()`, always-on). Results: mass error reduced from O(10^-3) to **machine precision O(10^-15)** with negligible impact on shape error L₂.

### Key Discovery: Accidental Error Cancellation

Before the fix, reinitialization accidentally **added** mass (+21.57 cumulative, N=128 Zalesak) that partially cancelled advection losses (-38.48). Fixing reinit alone made mass error *worse* (1.08e-3 → 2.36e-3). Both advection and reinit corrections were required.

### Grid Convergence (Single Vortex)

| N | L₂ | L∞ | L₂ order |
|---:|:------:|:------:|:--------:|
| 64 | 1.91e-1 | 8.64e-1 | — |
| 128 | 1.73e-1 | 7.99e-1 | 0.14 |
| 256 | 1.43e-1 | 7.25e-1 | 0.28 |
| 512 | 1.05e-1 | 7.00e-1 | 0.44 |

Shape error convergence is slow (~O(h^0.4)) due to CLS filaments thinning below grid resolution during vortex stretching — a resolution limit, not a conservation issue.

See full analysis in `docs/memo/cls_reinit_mass_conservation.md`.
