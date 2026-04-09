---
ref_id: WIKI-E-009
title: "CLS Shape Preservation: Parameter Study and Adaptive Reinitialization"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch11/exp11_19_shape_preservation.py
    git_hash: null
    description: "4-priority parameter study: eps_d, eps/h, adaptive reinit, RK3 pseudo-time"
  - path: docs/memo/cls_shape_preservation.md
    git_hash: null
    description: "Short paper with full analysis, physical interpretation, and recommendations"
consumers:
  - domain: L
    description: "Reinitializer — adaptive trigger recommended for production"
  - domain: T
    description: "Revises understanding of CLS shape error sources"
depends_on:
  - "[[WIKI-T-028]]: CLS-DCCD conservation theory (mass-loss root causes)"
  - "[[WIKI-E-003]]: LS transport experiments (single vortex baseline)"
  - "[[WIKI-T-007]]: CLS transport and reinitialization theory"
tags: [CLS, shape-preservation, reinitialization, adaptive, parameter-study]
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-09
---

## Key Finding

**Interface thickness ε is the dominant shape error source in φ-space** — reinitialization frequency is secondary. The original ψ-space analysis overstated the reinit contribution because ψ-L₂ is ε-dependent ([[WIKI-T-029]]). In φ-space: ε/h=1.5→1.0 gives **−32.6%**, adaptive reinit gives **−21.4%**, combined **−47.0%**.

## Experiment Design

Single vortex (LeVeque 1996), N=128, deform + time-reverse (T=8.0). Four parameters tested independently then combined:

| Priority | Parameter | Range | Hypothesis |
|---|---|---|---|
| P1 | ε_d (filter strength) | 0.05, 0.025, 0.01, 0.0 | Lower damping → less diffusion |
| P2 | ε/h (interface thickness) | 2.0, 1.5, 1.0, 0.75 | Thinner → sharper features |
| P3 | Reinit strategy | fixed-10, fixed-20, adaptive-{1.05,1.10,1.20}, none | Less reinit → less damage |
| P4 | Reinit time integration | FE-4, RK3-4, FE-8, RK3-2 | Higher order → better accuracy |

## Results

### P1: ε_d — Negligible Impact

| ε_d | L₂(ψ) | L₂(φ) | Δφ |
|---|---|---|---|
| 0.050 | 1.735e-01 | 3.427e-02 | baseline |
| 0.025 | 1.755e-01 | 3.451e-02 | −0.7% |
| 0.010 | 1.762e-01 | 3.449e-02 | −0.6% |
| 0.000 | 1.775e-01 | 3.452e-02 | −0.7% |

Negligible in both metrics. DCCD damping is irrelevant for smooth CLS profiles.

### P2: ε/h — **Dominant** Improvement (φ-space corrected)

| ε/h | L₂(ψ) | Δψ | L₂(φ) | Δφ |
|---|---|---|---|---|
| 2.00 | 1.856e-01 | −7.0% | 4.524e-02 | −32.0% |
| 1.50 | 1.735e-01 | baseline | 3.427e-02 | baseline |
| 1.00 | 1.475e-01 | +15.0% | 2.310e-02 | **+32.6%** |
| 0.75 | 1.292e-01 | +25.6% | 1.777e-02 | **+48.1%** |

**ψ-space understated this by 2×.** In φ-space, ε/h=1.0 gives 32.6% improvement (vs 15.0% in ψ). This is because thinner ε has steeper ψ gradients, inflating ||Δψ|| even when the interface position is accurate.

### P3: Adaptive Reinit — Important but Not Dominant

| Strategy | L₂(ψ) | Δψ | L₂(φ) | Δφ |
|---|---|---|---|---|
| fixed-10 | 1.735e-01 | baseline | 3.427e-02 | baseline |
| fixed-20 | 1.750e-01 | −0.9% | 3.429e-02 | −0.0% |
| adaptive-1.05 | 1.184e-01 | +31.8% | 2.986e-02 | +12.9% |
| **adaptive-1.10** | **8.896e-02** | **+48.7%** | **2.696e-02** | **+21.4%** |
| adaptive-1.20 | 1.192e-01 | +31.3% | 2.990e-02 | +12.8% |
| no-reinit | 6.700e-02 | +61.4% | 2.341e-02 | +31.7% |

**ψ-space overstated adaptive reinit by 2.3×** (48.7% → 21.4%). Much of the ψ-L₂ improvement comes from avoiding profile reshaping (a ψ artifact), not from better interface positioning.

### P4: TVD-RK3 Reinit — RK3-2step beneficial in φ-space

| Config | L₂(ψ) | Δψ | L₂(φ) | Δφ |
|---|---|---|---|---|
| FE-4step | 1.735e-01 | baseline | 3.427e-02 | baseline |
| RK3-4step | 1.910e-01 | −10.1% | 3.206e-02 | +6.4% |
| FE-8step | 1.790e-01 | −3.2% | 3.494e-02 | −2.0% |
| RK3-2step | 1.690e-01 | +2.6% | 2.950e-02 | **+13.9%** |

RK3-4step: ψ-space showed it worse; φ-space shows it **better** (+6.4%). RK3-2step is clearly beneficial in both metrics.

### Combined

| Config | L₂(ψ) | Δψ | L₂(φ) | Δφ | Reinits |
|---|---|---|---|---|---|
| baseline | 1.735e-01 | — | 3.427e-02 | — | 227 |
| best-eps | 1.475e-01 | +15.0% | 2.310e-02 | **+32.6%** | 227 |
| best-adaptive | 8.896e-02 | +48.7% | 2.696e-02 | +21.4% | 2 |
| combined-123 | 9.395e-02 | +45.9% | 2.000e-02 | **+41.7%** | 2 |
| **combined-all** | **7.099e-02** | **+59.1%** | **1.817e-02** | **+47.0%** | 4 |

## Revised Understanding (φ-space corrected, WIKI-T-029)

The original ψ-space hierarchy was **misleading**. φ-space reveals the true error structure:

| Factor | ψ-space Δ | φ-space Δ | Discrepancy |
|---|---|---|---|
| **Interface ε** (1.5→1.0) | +15.0% | **+32.6%** | ψ understated 2.2× |
| **Adaptive reinit** | +48.7% | +21.4% | ψ overstated 2.3× |
| **DCCD filter** | −2.1% | −0.7% | Both negligible |

**Root cause of discrepancy**: ψ = H_ε(φ) has ε-dependent gradients. Changing ε changes ||Δψ|| even for identical interface displacement. Reinitialization reshapes the ψ profile (affecting ||Δψ||) without necessarily moving the interface (which ||Δφ|| measures). See [[WIKI-T-029]] for the theoretical derivation.

## Recommendation (revised)

1. **ε/h=1.0** is the highest-priority improvement (−32.6% in φ-space)
2. **Adaptive reinit (1.10)** is secondary but still valuable (−21.4%)
3. **Combined** yields −47.0% in φ-space
4. **Use L₂(φ) as primary metric** for all CLS shape comparisons ([[WIKI-T-029]])
