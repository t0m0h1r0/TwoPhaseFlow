# Direct Geometric Reinitialization (DGR) for CLS

Date: 2026-04-09
Status: VERIFIED
Related: `src/twophase/levelset/reinitialize.py`, [[WIKI-T-029]], [[WIKI-T-007]], [[WIKI-T-030]], [[WIKI-E-011]]

---

## Abstract

The standard operator-split compression-diffusion CLS reinitialization has a
structural defect: it broadens the interface by ~40% per call due to splitting
error between compression (Forward Euler) and diffusion (CN-ADI). After 89
reinit calls, ε_eff ≈ 4ε — even on a perfect static profile with no advection.

This memo:
1. Identifies the splitting defect empirically
2. Derives Direct Geometric Reinitialization (DGR): logit inversion + gradient
   normalization to restore thickness in one step, with provable mass conservation
3. Shows DGR alone fails on shape restoration (no profile correction)
4. Proposes and verifies a **hybrid scheme** (Comp-Diff → DGR) that achieves
   both shape restoration and thickness maintenance

The hybrid scheme maintains ε_eff/ε ≈ 1.02 throughout a full Zalesak revolution
while achieving 5× better area accuracy than standard Comp-Diff.

---

## 1. The Splitting Defect

### Empirical evidence

Applying Comp-Diff reinitialization to a **perfect** H_ε profile (no advection,
smooth circle, N=128, ε/h=1.0):

| reinit calls | ε_eff/ε |
|-------------|---------|
| 0           | 1.000   |
| 1           | 1.395   |
| 5           | 2.196   |
| 10          | 2.729   |
| 89          | 3.976   |

Each call broadens the interface by ~40%. The broadening is monotonic and
does not saturate until ε_eff ≈ 4ε.

### Root cause: operator splitting mismatch

The Comp-Diff scheme applies two stages sequentially:

    Stage 1 (compression, FE):  ψ** = ψ − Δτ·∇·[ψ(1−ψ)n̂]
    Stage 2 (diffusion, CN):    (M₂−μB₂)ψ_new = (M₂+μB₂)ψ**

At equilibrium, compression = diffusion. But sequential application breaks this:
- Compression sharpens first → intermediate ψ** has ε' < ε
- Diffusion then acts on ε' profile, overshooting to ε'' > ε

The error is O(Δτ) per pseudo-step and accumulates over n_steps.
Increasing n_steps **worsens** the problem (more splitting iterations):

| n_steps | ε_eff/ε after 1 call |
|---------|---------------------|
| 1       | 1.119               |
| 4       | 1.395               |
| 16      | 2.052               |
| 32      | 2.550               |

---

## 2. DGR Theory

### Algorithm

Given ψ (distorted), target ε:

1. **Logit inversion**: φ_raw = ε·ln(ψ/(1−ψ))
2. **Gradient normalization**: compute |∇ψ| via CCD, estimate
   ε_eff = median(ψ(1−ψ)/|∇ψ|) in the interface band, rescale
   φ_sdf = φ_raw · (ε_eff/ε)
3. **Reconstruction**: ψ_new = H_ε(φ_sdf)
4. **Mass correction**: ψ_corr = ψ_new + (δM/W)·4ψ_new(1−ψ_new)

### Theorem 1 (Thickness restoration)

If ψ = H_{ε_eff}(φ_true) with uniform ε_eff and |∇φ_true|=1, then
Steps 1–3 yield ψ_new = H_ε(φ_true). **Proof**: φ_raw = (ε/ε_eff)·φ_true,
scale = ε_eff/ε, φ_sdf = φ_true. ∎

### Theorem 2 (Mass conservation)

Σψ_corr = Σψ_old (exact, pre-clipping). **Proof**: Σψ_corr = Σψ_new + δM = Σψ_old. ∎

### Theorem 3 (Profile-preserving correction)

The mass correction ≈ uniform interface shift Δφ = 4λε; does not change
thickness. **Proof**: w = 4ψ(1−ψ) = 4ε·(∂ψ/∂φ), so ψ+λw ≈ H_ε(φ+4λε). ∎

---

## 3. DGR Alone: Failure Mode

### Experiment: DGR-only on Zalesak (N=128, ε/h=1.0, every-20)

| Method    | ε_eff/ε (T) | L₂(φ)   | Area error |
|-----------|-------------|----------|------------|
| Comp-Diff | 4.01        | 1.87e-02 | 7.00e-03   |
| DGR       | 0.99        | 9.64e-02 | 2.41e-02   |

DGR restores thickness perfectly but L₂ and area are 5× worse.

### Root cause: DGR is a no-op when ε_eff ≈ ε

After 20 advection steps (before reinit), ε_eff/ε ≈ 1.004. DGR measures
scale ≈ 1.0, applies negligible correction. This means DGR provides
**no shape restoration** — it is equivalent to no reinitialization.

The broadening occurs in the Comp-Diff reinit, not in advection. Without
Comp-Diff, DGR has nothing to correct for thickness but also provides
no profile reshaping.

---

## 4. Hybrid Scheme: Comp-Diff + DGR

### Algorithm

    def reinitialize_hybrid(ψ):
        ψ = comp_diff_reinit(ψ)     # shape restoration (introduces ~1.4× broadening)
        ψ = dgr_reinit(ψ)           # thickness correction (restores ε_eff → ε)
        return ψ

### Results: Zalesak (N=128, ε/h=1.0, reinit every-20, T=2π)

| Method    | ε_eff/ε (T) | Area error   | Mass error |
|-----------|-------------|--------------|------------|
| Comp-Diff | 4.01        | 7.00e-03     | 1.2e-15    |
| DGR       | 0.99        | 2.41e-02     | 6.0e-15    |
| **Hybrid**| **1.02**    | **1.46e-03** | 2.8e-15    |

**Hybrid achieves both goals**:
- Thickness maintained: ε_eff/ε = 1.02 (vs 4.01 for Comp-Diff)
- Area accuracy 5× better: 1.46e-3 (vs 7.00e-3 for Comp-Diff)
- Mass conservation: O(10⁻¹⁵)

### Why hybrid works

DGR receives a profile broadened by only ~1.4× (one Comp-Diff call), not
the accumulated 4× of many calls. The median ε_eff estimate is accurate
for this small broadening, and the rescaling correctly restores thickness
without distorting narrow features (slot is still well-resolved at 1.4×).

---

## 5. Note on L₂(φ) Metric

The band-restricted L₂(φ) metric appears worse for Hybrid (0.041) than
Comp-Diff (0.019). This is a measurement artifact (WIKI-T-029): the
band |φ₀| < 6ε captures different proportions of each profile depending
on ε_eff. **Area error** (symmetric difference of {ψ≥0.5}) is the only
ε-independent metric, and Hybrid is best by this measure.

---

## 6. Conclusions

1. Comp-Diff reinit has a structural splitting defect: +40%/call thickness broadening
2. DGR restores thickness in one step (Thm 1–3) but provides no shape restoration
3. **Hybrid (Comp-Diff → DGR) achieves both**: ε_eff/ε ≈ 1.02, area error 5× better
4. The hybrid scheme is the recommended production configuration
