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

| εd_adv | L₂(ψ)    | L₂(φ)    | Δφ      |
|--------|-----------|----------|---------|
| 0.000  | 8.962e-02 | 2.437e-02 | −1.5%  |
| 0.010  | 9.008e-02 | 2.440e-02 | −1.4%  |
| 0.025  | 9.112e-02 | 2.450e-02 | −1.0%  |
| 0.050  | 9.350e-02 | 2.474e-02 | baseline|

φ-space: εd effect is only 1.5% (vs 4.1% in ψ-space). ψ-space overstated the DCCD impact because the ψ metric is gradient-sensitive.

### S2: Reinit compression εd — must retain

| εd_reinit | L₂(φ)    | Δφ      |
|-----------|----------|---------|
| 0.000     | 2.481e-02 | +0.3%  |
| 0.050     | 2.474e-02 | baseline|

Conclusion unchanged: removing compression DCCD slightly worsens results.

### S3: Reinit frequency — every-20 optimal for sharp geometry

| Frequency | L₂(ψ)    | L₂(φ)    | Δφ       |
|-----------|-----------|----------|----------|
| every 10  | 9.774e-02 | 2.512e-02 | +1.5%   |
| every 20  | 9.350e-02 | 2.474e-02 | baseline |
| every 40  | 1.747e-01 | 2.573e-02 | +4.0%   |
| every 80  | 2.564e-01 | 1.152e-01 | +366%   |

φ-space reveals every-40 is only 4% worse (vs 87% in ψ-space) — the ψ metric exaggerated the profile-broadening effect. Only every-80 shows true catastrophic failure.

### S4: Combined best — 26.8% improvement in φ-space

| Configuration                    | L₂(ψ)    | Δψ         | L₂(φ)    | Δφ         |
|----------------------------------|-----------|------------|----------|------------|
| εd_adv=0, ε/h=1.0, every-20     | 8.350e-02 | −10.7%     | 1.810e-02 | **−26.8%** |
| εd_adv=0, ε/h=1.5, every-20     | 8.962e-02 | −4.1%      | 2.437e-02 | −1.5%      |
| baseline (all defaults)          | 9.350e-02 | —          | 2.474e-02 | —          |

**Critical revision**: ψ-space showed 10.7% improvement; φ-space shows **26.8%**. The dominant factor is ε/h=1.0 (−25.3% alone in φ), not εd reduction (−1.5%).

## Revised Understanding (φ-space corrected)

Error hierarchy for **sharp geometry** (Zalesak), measured in φ-space:

| Factor               | Zalesak L₂(φ) Δ     | Smooth circle L₂(φ) Δ (WIKI-E-009) |
|----------------------|----------------------|--------------------------------------|
| Interface ε (1.5→1.0)| **−25.3% (dominant)**| −32.6% (dominant)                    |
| Reinit frequency     | mandatory (every-20) | adaptive →−21.4%                     |
| Advection DCCD       | −1.5%                | −0.7%                                |
| Reinit DCCD          | keep (stability)     | ~0%                                  |

**Hierarchy inversion**: In ψ-space, adaptive reinit appeared dominant (+49%); in φ-space, **interface thickness ε is the dominant factor** for both smooth and sharp geometry. The ψ-space metric inflated the reinit contribution because reinitialization reshapes the ψ profile (affecting ||Δψ||) without necessarily moving the interface position (which ||Δφ|| measures).

## Recommendation (revised)

- **ε/h=1.0** is the highest-priority improvement (−25% in φ-space)
- **εd_adv reduction** has minimal benefit in φ-space (−1.5%) — not worth the stability risk
- **every-20 reinit** remains necessary for Zalesak (every-80 catastrophic)
- **ψ-space L₂ should not be used for cross-ε comparisons** (see [[WIKI-T-029]])
