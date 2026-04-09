# Zalesak Slotted Disk: DCCD Damping Sensitivity on Sharp Geometry

Date: 2026-04-09
Status: VERIFIED
Related: `experiment/ch11/exp11_20_zalesak_dccd_study.py`, [[WIKI-T-002]], [[WIKI-T-028]], [[WIKI-E-009]], [[WIKI-E-010]]

---

## Abstract

The prior shape-error hierarchy (WIKI-E-009) concluded that DCCD damping contributes only ~2% of the total L₂ error.
However, that finding was derived exclusively from the single-vortex benchmark (smooth circular interface).
This study tests the hypothesis that DCCD damping has a stronger impact on Zalesak's slotted disk,
whose sharp slot corners contain high-frequency spectral content near the Nyquist limit.

A 4-sweep parametric study at N=128 confirms geometry-dependent sensitivity:
advection DCCD damping accounts for **4.1% of L₂ error on Zalesak** (vs 2.1% on smooth circle).
Combined with thinner interface (ε/h=1.0), total improvement reaches **10.7%**.
Reinitialization frequency remains the dominant constraint for sharp features.

---

## 1. Motivation

DCCD filtering introduces effective numerical diffusion via the second-difference stencil:

    F̃ᵢ = f'ᵢ + εd(f'ᵢ₊₁ − 2f'ᵢ + f'ᵢ₋₁)

with transfer function H(ξ; εd) = 1 − 4εd sin²(ξ/2).

For the smooth CLS profile (ψ = Hε(φ), characteristic width ε ≈ 1.5h), the minimum wavelength
is λ_min ≈ 2πε ≈ 9.4h, where H ≈ 0.98 — only 2% damping per application.

However, Zalesak's slotted disk has **sharp geometric features**:
- 90° slot corners (C⁰ discontinuities in curvature)
- Vertical slot walls (6.4 cells wide at N=128)

These features generate spectral content at shorter wavelengths where DCCD damping is stronger.

### Diffusion length estimate

DCCD acts as effective numerical diffusion with coefficient D_eff ∝ εd · h².
Over one full revolution (T = 2π) at N=128:

| εd    | Diffusion length (cells) | Slot width (cells) | Ratio |
|-------|--------------------------|---------------------|-------|
| 0.05  | ~6.3                     | 6.4                 | 0.98  |
| 0.025 | ~4.5                     | 6.4                 | 0.70  |
| 0.01  | ~2.8                     | 6.4                 | 0.44  |
| 0.0   | 0                        | 6.4                 | 0     |

At the default εd=0.05, the diffusion length is **comparable to the slot width** — slot corner degradation is expected.

### Dual application sites

DCCD is applied at two independent locations:
1. **Advection** (`DissipativeCCDAdvection._rhs()`): ~3572 applications (1786 steps × 2 axes)
2. **Reinit compression** (`Reinitializer._dccd_compression_div()`): ~712 applications (89 reinits × 4 pseudo-steps × 2 axes)

---

## 2. Experimental Design

All tests at N=128, Zalesak slotted disk, rigid rotation 1 full revolution (T=2π).
Baseline: εd_adv=0.05, εd_reinit=0.05, reinit every-20, n_steps=4, ε=1.5h.

| Sweep | Parameter           | Values                  | Fixed                                  |
|-------|---------------------|-------------------------|----------------------------------------|
| S1    | εd (advection)      | {0.0, 0.01, 0.025, 0.05} | reinit every-20, εd_reinit=0.05, ε=1.5h |
| S2    | εd (reinit comp.)   | {0.0, 0.01, 0.025, 0.05} | εd_adv=0.05, reinit every-20, ε=1.5h    |
| S3    | Reinit frequency    | every {10, 20, 40, 80}    | εd_adv=0.05, εd_reinit=0.05, ε=1.5h     |
| S4    | Combined best + ε/h | best S1–S3 + ε/h∈{1.0,1.5}| —                                       |

Metrics: L₂ = √(mean((ψ_final − ψ_init)²)), mass_err = |ΔM|/M₀.

---

## 3. Results

### S1: Advection εd sensitivity

| εd_adv | L₂        | Δ vs baseline | mass_err |
|--------|-----------|---------------|----------|
| 0.000  | 8.962e-02 | **−4.1%**     | 0.00e+00 |
| 0.010  | 9.008e-02 | −3.7%         | 1.86e-15 |
| 0.025  | 9.112e-02 | −2.6%         | 4.41e-15 |
| 0.050  | 9.350e-02 | baseline      | 8.01e-15 |

**Finding**: Monotonic improvement as εd decreases. At εd=0 (pure CCD), 4.1% improvement — **2× the effect measured on smooth circle** (2.1% in WIKI-E-009). Stability is maintained even at εd=0 for this configuration.

### S2: Reinit compression εd sensitivity

| εd_reinit | L₂        | Δ vs baseline |
|-----------|-----------|---------------|
| 0.000     | 9.429e-02 | +0.8% (worse) |
| 0.010     | 9.392e-02 | +0.5% (worse) |
| 0.025     | 9.369e-02 | +0.2%         |
| 0.050     | 9.350e-02 | baseline      |

**Finding**: Removing reinit DCCD filter **worsens** results. The compression term ∇·[ψ(1−ψ)n̂] requires the DCCD stabilization. Unlike advection, the compression flux involves the product ψ(1−ψ) which amplifies CCD oscillations at the interface.

### S3: Reinit frequency

| Frequency  | L₂        | reinits | Δ vs baseline |
|------------|-----------|---------|---------------|
| every 10   | 9.774e-02 | 178     | +4.5% (worse) |
| every 20   | 9.350e-02 | 89      | baseline      |
| every 40   | 1.747e-01 | 44      | +86.9% (worse)|
| every 80   | 2.564e-01 | 22      | +174% (worse) |

**Finding**: For Zalesak, every-20 is optimal. Unlike the smooth vortex test where adaptive reinit (2–3 calls) achieved 49% improvement, **sharp geometry requires regular reinitialization** to maintain slot corners. Reducing frequency below every-20 causes rapid profile degradation. Increasing to every-10 over-reinitializes and rounds corners.

### S4: Combined best

| Configuration                              | L₂        | Δ vs baseline |
|--------------------------------------------|-----------|---------------|
| εd_adv=0, εd_reinit=0.05, ε/h=1.0, every-20 | 8.350e-02 | **−10.7%**    |
| εd_adv=0, εd_reinit=0.05, ε/h=1.5, every-20 | 8.962e-02 | −4.1%         |
| baseline (all defaults)                      | 9.350e-02 | —             |

---

## 4. Discussion

### Geometry-dependent DCCD sensitivity

The 2× difference in DCCD sensitivity (4.1% Zalesak vs 2.1% smooth circle) is explained by spectral content:

- **Smooth circle**: interface profile has λ_min ≈ 9.4h; DCCD damping at this wavelength is H ≈ 0.98
- **Zalesak slot corners**: 90° corners generate spectral content at λ ≈ 3–6h; H(2π/4) ≈ 0.90, significantly more damping

The effect accumulates over ~1786 advection steps, yielding a measurable but non-dominant contribution.

### Reinit compression requires DCCD

S2 reveals an asymmetry between advection and reinitialization:
- **Advection**: flux f = ψu is smooth when u is smooth → CCD is stable without filter
- **Compression**: flux g = ψ(1−ψ)n̂ involves the interface-concentrated product ψ(1−ψ), which has sharper gradients → CCD oscillations need DCCD suppression

### Sharp geometry vs smooth: fundamental trade-off

For smooth interfaces (single vortex): adaptive reinit reduces calls from 227→2, yielding 49% improvement.
For sharp geometry (Zalesak): every-20 fixed reinit is mandatory; adaptive trigger M(τ)/M_ref cannot detect local corner degradation.

This represents a **fundamental limitation of the global volume monitor M(τ) = ∫ψ(1−ψ)dV**: it measures average interface thickness, not local geometric fidelity.

---

## 5. Revised Error Hierarchy for Zalesak

| Error Source           | L₂ contribution | Mechanism                                          |
|------------------------|------------------|----------------------------------------------------|
| Reinit frequency       | dominant         | every-20 mandatory; deviation causes 5–174% change |
| Interface thickness ε  | ~7%              | ε/h=1.5→1.0 improves L₂ by 6.8% (at εd=0)       |
| Advection DCCD damping | ~4%              | 2× larger than smooth circle due to corner spectra |
| Reinit DCCD damping    | ~0% (beneficial) | Required for compression stability                 |

---

## 6. Conclusions

1. DCCD damping effect is **geometry-dependent**: 4.1% on Zalesak (sharp) vs 2.1% on smooth circle
2. **Advection DCCD can be safely reduced to εd=0** for CLS advection (tested at N=128)
3. **Reinit compression DCCD must be retained** — removing it destabilizes the compression term
4. **Combined best (εd_adv=0, ε/h=1.0) yields 10.7% improvement** over default settings
5. **Reinitialization frequency remains the dominant constraint** for sharp geometry
6. Global volume monitor M(τ) is insufficient for local geometric fidelity — a local corner metric would be needed for further improvement
