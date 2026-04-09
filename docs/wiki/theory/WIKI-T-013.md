---
ref_id: WIKI-T-013
title: "WENO5 Reference Scheme & DCCD Comparative Advection Experiments"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/appendix_numerics_schemes_s2.tex
    git_hash: 3d4d1bb
    description: "WENO5 complete formulation: Lax-Friedrichs splitting, smoothness indicators, reconstruction"
  - path: paper/sections/appendix_numerics_schemes_s3.tex
    git_hash: 3d4d1bb
    description: "O2/O4/CCD/DCCD/WENO5 1D linear advection benchmark: waveform, L2 error, TV analysis"
consumers:
  - domain: L
    usage: "advection.py WENO5 kernel (_weno5_pos/_weno5_neg); DCCD filter implementation"
  - domain: A
    usage: "Appendix C.1–C.2 referenced from §7 (advection motivation)"
  - domain: E
    usage: "Benchmark results inform scheme selection for CLS advection"
depends_on:
  - "[[WIKI-T-002]]"
  - "[[WIKI-T-001]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## C.1 — WENO5 Reference Scheme

WENO5 serves as the comparison baseline for DCCD. Not the primary implementation — DCCD is preferred for CLS advection.

### Lax-Friedrichs Flux Splitting

F⁺(q) = ½(F + α q), F⁻(q) = ½(F − α q), where α = max|u| (global LF). Global LF preferred for two-phase: density ratio causes large wave speed variation near interface.

### Smoothness Indicators (β_k)

β₀ = (13/12)(f_{i-2}−2f_{i-1}+f_i)² + (1/4)(f_{i-2}−4f_{i-1}+3f_i)²
β₁ = (13/12)(f_{i-1}−2f_i+f_{i+1})² + (1/4)(f_{i-1}−f_{i+1})²
β₂ = (13/12)(f_i−2f_{i+1}+f_{i+2})² + (1/4)(3f_i−4f_{i+1}+f_{i+2})²

### Nonlinear Weights

Ideal: d₀=1/10, d₁=3/5, d₂=3/10. Then α_k = d_k/(ε_w+β_k)², ω_k = α_k/Σα_j.

### Reconstruction Coefficients (positive flux)

f̂₀⁺ = (1/3)F⁺_{i-2} − (7/6)F⁺_{i-1} + (11/6)F⁺_i
f̂₁⁺ = −(1/6)F⁺_{i-1} + (5/6)F⁺_i + (1/3)F⁺_{i+1}
f̂₂⁺ = (1/3)F⁺_i + (5/6)F⁺_{i+1} − (1/6)F⁺_{i+2}

Negative flux: mirror index. Total: F̂_{i+½} = F̂⁺ + F̂⁻.

### Properties

- O(h⁵) in smooth regions; ENO-like oscillation suppression near discontinuities
- Conservative (flux-form): discrete mass conservation exact
- 5-point stencil (6 points total with negative flux)
- Boundary: ghost cells (periodic wrap / symmetric reflection / constant extrapolation)

## C.2 — DCCD vs WENO5: 1D Linear Advection Benchmark

**Setup:** ∂u/∂t + u_x = 0, x∈[0,1), periodic, T=1 (one period). N=256, RK4, CFL=0.4.

**D10 selective filter (DCCD):** u*_i = u_i + α_f Σ d_k u_{i+k}, α_f=0.4. Coefficients: d_k = (−1)^{k+1} C(10,5−k)/2¹⁰. Filter eigenvalue: 0 at ξ=0, −1 at ξ=π. Transfer function ∈ [0.6, 1.0].

### L² Error Results (N=256)

| Initial condition | O2 | O4 | CCD | DCCD | WENO5 |
|---|---|---|---|---|---|
| Square (discontinuous) | 1.41e-1 | 9.08e-2 | 4.80e-2 | **4.23e-2** | 6.35e-2 |
| Triangle (C⁰) | 2.41e-2 | 5.84e-3 | **1.37e-3** | 1.41e-3 | 3.90e-3 |
| Tanh (C^∞) | 3.75e-2 | 2.46e-3 | **2.57e-5** | 3.75e-5 | 9.66e-4 |

### TV Ratio (TV/TV_exact)

| Initial condition | O2 | O4 | CCD | DCCD | WENO5 |
|---|---|---|---|---|---|
| Square | 9.20 | 8.58 | 5.42 | 1.58 | **1.00** |
| Triangle | 1.32 | 1.20 | 1.06 | **1.00** | 0.97 |
| Tanh | 1.41 | 1.01 | **1.00** | **1.00** | **1.00** |

### Key Findings

1. **Discontinuous:** WENO5 best TV (1.00) but DCCD best L² (1.5× better)
2. **C⁰ corners:** CCD best L²; DCCD uniquely achieves TV=1.00; WENO5 slightly over-dissipates (0.97)
3. **C^∞ smooth:** CCD best L² (2.57e-5); WENO5 is 38× worse due to O(h⁵) + ENO overhead
4. **CLS suitability:** DCCD optimal trade-off for sharp-yet-smooth CLS profiles
