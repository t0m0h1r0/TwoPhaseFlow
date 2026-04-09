---
ref_id: WIKI-E-011
title: "Hybrid Reinitialization: Splitting Defect Discovery and Comp-Diff + DGR Fix"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: docs/memo/direct_geometric_reinit.md
    git_hash: null
    description: "Full theory, DGR proofs, splitting defect analysis, hybrid verification"
  - path: src/twophase/levelset/reinitialize.py
    git_hash: null
    description: "Implementation: method='hybrid' (Comp-Diff + DGR)"
consumers:
  - domain: L
    description: "reinitialize.py — hybrid is recommended production method"
  - domain: T
    description: "Revises understanding of reinit thickness dynamics"
depends_on:
  - "[[WIKI-T-030]]: DGR theory (logit inversion, gradient normalization, mass conservation)"
  - "[[WIKI-T-029]]: Error metric — area error is the ε-independent metric"
  - "[[WIKI-T-007]]: CLS reinitialization theory"
  - "[[WIKI-E-010]]: Zalesak DCCD study (baseline comparison)"
tags: [CLS, reinitialization, splitting-error, DGR, hybrid, thickness]
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-09
---

## Key Finding

**Operator-split Comp-Diff reinitialization broadens the interface by ~40% per call** — a structural defect from sequential compression→diffusion application. After 89 calls: ε_eff ≈ 4ε. This occurs even on a perfect static profile with no advection.

**Hybrid (Comp-Diff → DGR)** fixes this: Comp-Diff restores profile shape, then DGR corrects the splitting-induced broadening. Result: ε_eff/ε ≈ 1.02 with **5× better area accuracy**.

## Splitting Defect: Empirical Evidence

Comp-Diff applied to a **perfect** H_ε(φ) profile (no advection, smooth circle, N=128):

| reinit calls | ε_eff/ε |
|-------------|---------|
| 0           | 1.000   |
| 1           | 1.395   |
| 10          | 2.729   |
| 89          | 3.976   |

Increasing n_steps worsens it: n_steps=32 → ε_eff/ε = 2.55 after 1 call.

**Mechanism**: compression (FE) sharpens to ε' < ε, then diffusion (CN-ADI) overshoots to ε'' > ε. The O(Δτ) splitting error accumulates monotonically.

## Three Methods Compared

Zalesak slotted disk, N=128, ε/h=1.0, reinit every-20, full revolution T=2π.

| Method    | ε_eff/ε (T) | Area error   | Mass error | Notes |
|-----------|-------------|--------------|------------|-------|
| Comp-Diff | 4.01        | 7.00e-03     | 1.2e-15    | Shape OK, thickness fails |
| DGR       | 0.99        | 2.41e-02     | 6.0e-15    | Thickness OK, no shape fix |
| **Hybrid**| **1.02**    | **1.46e-03** | 2.8e-15    | Both OK |

## Why DGR Alone Fails

After 20 advection steps: ε_eff/ε ≈ 1.004. DGR detects scale ≈ 1.0 → no-op.
The broadening originates in Comp-Diff reinit, not advection. Without Comp-Diff,
DGR has nothing to correct for thickness and provides no shape restoration.

## Why Hybrid Works

1. Comp-Diff restores sigmoid shape (compression + diffusion) but introduces ~1.4× broadening
2. DGR immediately corrects: median ε_eff ≈ 1.4ε → rescale φ by 1.4 → reconstruct H_ε(φ_true)
3. Small correction (1.4×, not 4×) → median ε_eff estimate is accurate, narrow features preserved

## Recommendation

- **Use `method='hybrid'`** for all CLS simulations
- Area error is the reliable metric for cross-ε comparisons ([[WIKI-T-029]])
- L₂(φ) in band |φ₀| < 6ε is ε_eff-dependent and misleading for hybrid vs Comp-Diff comparison
