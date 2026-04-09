---
ref_id: WIKI-E-010
title: "Zalesak Slotted Disk: DCCD Damping Sensitivity on Sharp Geometry"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch11/exp11_20_zalesak_dccd_study.py
    git_hash: null
    description: "4-sweep parametric study: adv εd, reinit εd, reinit frequency, combined"
  - path: docs/memo/zalesak_dccd_damping.md
    git_hash: null
    description: "Short paper with diffusion-length analysis and full results"
consumers:
  - domain: L
    description: "advection.py — εd=0 viable for CLS; reinitialize.py — eps_d_comp parameter added"
  - domain: T
    description: "Extends WIKI-E-009 hierarchy to sharp geometry; geometry-dependent damping"
depends_on:
  - "[[WIKI-T-002]]: DCCD filter theory and transfer function"
  - "[[WIKI-T-028]]: CLS-DCCD conservation theory"
  - "[[WIKI-E-009]]: Shape preservation on smooth circle (baseline comparison)"
tags: [CLS, DCCD, Zalesak, sharp-geometry, damping, parametric-study]
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-09
---

## Key Finding

**DCCD damping sensitivity is geometry-dependent**: advection εd accounts for 4.1% of L₂ error on Zalesak's sharp slot corners — **2× the 2.1% measured on smooth circle** (WIKI-E-009). Combined with thinner interface (ε/h=1.0), removing advection DCCD yields **10.7% total improvement**. However, reinit compression DCCD must be retained for stability, and fixed-frequency reinitialization (every-20) remains the dominant constraint.

## Experiment Design

N=128, Zalesak slotted disk (slot width=0.05, R=0.15), rigid rotation 1 revolution (T=2π).

| Sweep | Parameter         | Values                    |
|-------|-------------------|---------------------------|
| S1    | εd (advection)    | {0.0, 0.01, 0.025, 0.05} |
| S2    | εd (reinit comp.) | {0.0, 0.01, 0.025, 0.05} |
| S3    | Reinit frequency  | every {10, 20, 40, 80}    |
| S4    | Combined best     | best S1–S3 + ε/h ∈ {1.0, 1.5} |

## Results

### S1: Advection εd — monotonic improvement

| εd_adv | L₂        | Δ       |
|--------|-----------|---------|
| 0.000  | 8.962e-02 | −4.1%   |
| 0.010  | 9.008e-02 | −3.7%   |
| 0.025  | 9.112e-02 | −2.6%   |
| 0.050  | 9.350e-02 | baseline|

εd=0 is stable and improves accuracy. 4.1% effect vs 2.1% on smooth circle — sharp corners have higher-frequency content (λ≈3–6h vs λ≈9.4h).

### S2: Reinit compression εd — must retain

| εd_reinit | L₂        | Δ       |
|-----------|-----------|---------|
| 0.000     | 9.429e-02 | +0.8%   |
| 0.050     | 9.350e-02 | baseline|

Removing filter worsens results. Compression flux ψ(1−ψ)n̂ concentrates at the interface, amplifying CCD oscillations.

### S3: Reinit frequency — every-20 optimal for sharp geometry

| Frequency | L₂        | reinits | Δ       |
|-----------|-----------|---------|---------|
| every 10  | 9.774e-02 | 178     | +4.5%   |
| every 20  | 9.350e-02 | 89      | baseline|
| every 40  | 1.747e-01 | 44      | +86.9%  |
| every 80  | 2.564e-01 | 22      | +174%   |

Sharp slot corners require regular profile maintenance. Contrast: smooth circle benefits from adaptive reinit (2–3 calls, −49%).

### S4: Combined best — 10.7% improvement

| Configuration                    | L₂        | Δ       |
|----------------------------------|-----------|---------|
| εd_adv=0, ε/h=1.0, every-20     | 8.350e-02 | **−10.7%** |
| εd_adv=0, ε/h=1.5, every-20     | 8.962e-02 | −4.1%   |
| baseline (all defaults)          | 9.350e-02 | —       |

## Revised Understanding

Error hierarchy for **sharp geometry** (Zalesak) differs from smooth circle:

| Factor               | Zalesak (sharp)          | Smooth circle (WIKI-E-009) |
|----------------------|--------------------------|----------------------------|
| Reinit frequency     | **dominant** (every-20 mandatory) | dominant (adaptive →−49%) |
| Interface ε          | ~7%                      | ~15%                       |
| Advection DCCD       | ~4%                      | ~2%                        |
| Reinit DCCD          | beneficial (keep)        | ~0%                        |

Key difference: global volume monitor M(τ) cannot detect local corner degradation → adaptive reinit fails for sharp geometry.

## Recommendation

- **εd_adv=0** is safe for CLS advection (no stability issue observed)
- **εd_reinit=0.05** must be retained for compression stability
- **every-20 reinit** is optimal for Zalesak-class sharp features
- **ε/h=1.0** improves corner resolution (additional 6.8% on top of εd=0)
- For mixed-geometry simulations: use default εd=0.05 unless sharp-feature accuracy is priority
