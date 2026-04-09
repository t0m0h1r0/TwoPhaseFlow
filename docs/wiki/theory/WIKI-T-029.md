---
ref_id: WIKI-T-029
title: "CLS Error Metric: ψ-Space L₂ is ε-Dependent — φ-Space Comparison Required"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: src/twophase/levelset/heaviside.py
    git_hash: null
    description: "heaviside / invert_heaviside — forward and inverse H_ε transforms"
  - path: experiment/ch11/exp11_20_zalesak_dccd_study.py
    git_hash: null
    description: "Experiment where cross-ε comparison (S4) exposed the metric bias"
consumers:
  - domain: E
    description: "All CLS advection experiments (exp11_6, 11_18, 11_19, 11_20) — L₂ computation"
  - domain: T
    description: "WIKI-E-009, WIKI-E-010 — error hierarchy conclusions may need revision"
depends_on:
  - "[[WIKI-T-007]]: CLS transport and reinitialization theory"
  - "[[WIKI-T-002]]: DCCD filter theory"
tags: [CLS, error-metric, heaviside, inverse-transform, epsilon]
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-09
---

## Key Finding

**All CLS advection experiments compute L₂ error in ψ-space: ||ψ_final − ψ₀||₂.
This metric is ε-dependent and physically misleading for cross-ε comparisons.**

The CLS variable ψ = H_ε(φ) = 1/(1+exp(−φ/ε)) is a nonlinear, ε-parameterised
transform of the signed distance φ. For the same positional displacement Δx:

    ||Δψ|| ∝ (1/ε) · ||ψ(1−ψ) · Δx||

Thinner ε amplifies ψ-error; thicker ε suppresses it.

## Problem Description

### Current metric (all exp11_* CLS experiments)

```python
err_L2 = float(np.sqrt(np.mean((psi - psi0)**2)))   # ψ-space
```

### Issue 1: Within-ε comparisons are valid but not physically normalised

For S1–S3 sweeps (same ε=1.5h), the ψ-L₂ rankings are correct since the
metric bias is constant. However, the absolute L₂ values depend on ε and
are not directly comparable to literature values reported in φ-space.

### Issue 2: Cross-ε comparisons are biased

In exp11_20 S4, ε/h=1.0 gave L₂=0.0835 vs ε/h=1.5 gave L₂=0.0896.
These compare different initial conditions ψ₀ with different gradient magnitudes.
The ε/h=1.0 result appears only 6.8% better in ψ-space, but the actual
improvement in φ-space (physical distance) may be larger or smaller.

### Issue 3: `invert_heaviside` exists but is unused in experiments

`heaviside.py:76` provides `invert_heaviside(xp, psi, eps)` which computes
φ = ε·ln(ψ/(1−ψ)) with saturation handling. This is used in curvature
computation but never in error evaluation.

## Correct Approach

Convert to φ-space before computing L₂:

```python
phi_final = invert_heaviside(np, psi, eps)
err_L2_phi = float(np.sqrt(np.mean((phi_final - phi0)**2)))
```

### Caveats

1. **Saturation**: logit diverges at ψ→0,1. `invert_heaviside` clamps to
   ±φ_max ≈ 13.8ε, but bulk errors are mapped to flat ±φ_max, distorting L₂.
2. **Interface-band restriction**: To avoid saturation noise, restrict
   comparison to the interface band |φ₀| < kε (e.g., k=3 or k=6).
3. **Alternative metrics**: area error (symmetric difference of {ψ≥0.5})
   or contour-based Hausdorff distance avoid the saturation issue entirely.

## Affected Experiments

| Experiment | Cross-ε? | Impact |
|------------|----------|--------|
| exp11_6    | No (ε=1.5h fixed) | Rankings valid; absolute values ε-dependent |
| exp11_18   | No       | Valid |
| exp11_19   | Yes (P2: ε/h sweep) | **Biased** — P2 rankings may change |
| exp11_20   | Yes (S4: ε/h sweep) | **Biased** — S4 cross-ε comparison invalid |

## Recommendation

1. Add φ-space L₂ (interface-band restricted) as primary metric
2. Retain ψ-space L₂ as secondary metric for backward compatibility
3. Re-evaluate cross-ε conclusions in WIKI-E-009 (P2) and WIKI-E-010 (S4)
