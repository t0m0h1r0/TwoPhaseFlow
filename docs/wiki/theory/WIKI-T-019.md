---
ref_id: WIKI-T-019
title: "Filter Design for CCD: Compact Padé, Conservation-Preserving, and Geometric Filters"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: docs/memo/survey_filters_high_order_diff.md
    git_hash: e62cd50
    description: "Survey of low-pass filters compatible with CCD: Lele, Gaitonde-Visbal, Kim, Helmholtz-κ"
  - path: docs/memo/理論_CCD向けローパスフィルター.md
    git_hash: e62cd50
    description: "Conservation-preserving filter design: flux-form, implicit compact, LES approach"
  - path: docs/memo/interface_filter_ccd.md
    git_hash: e62cd50
    description: "CCD-native geometric filters: normal-vector diffusion, interface-limited κ filter"
consumers:
  - domain: L
    usage: "NormalVectorFilter, InterfaceLimitedFilter in levelset/ modules"
  - domain: A
    usage: "Filter theory referenced from §4 (DCCD) and §8 (PPE stability)"
depends_on:
  - "[[WIKI-T-002]]"
  - "[[WIKI-T-008]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## Problem

CCD computes κ = −∇·n via O(h⁶) derivatives. High-frequency noise in n propagates into κ, driving spurious currents via CSF. Standard DCCD 3-point filter acts on derivative fields, not geometric quantities — weak suppression of intermediate wavenumbers (kh ≈ 0.3–0.7).

## Compact Padé Filters (Aeroacoustics Heritage)

### Lele (1992) 6th-order

α_f f̂_{j-1} + f̂_j + α_f f̂_{j+1} = Σ (a_n/2)(f_{j+n} + f_{j-n})

α_f ∈ (−0.5, 0.5) free parameter. CCD-compatible: reuses tridiagonal infrastructure.

| α_f | H(π/4) | H(π/2) | H(3π/4) | H(π) |
|-----|--------|--------|---------|------|
| 0.45 | 0.9997 | 0.9971 | 0.961 | 0 |
| 0.30 | 0.9987 | 0.981 | 0.878 | 0 |
| 0.00 | 0.994 | 0.938 | 0.707 | 0 |

**Limitation:** α_f near 0.5 leaves intermediate modes (ξ ~ 0.3–0.5) almost untouched.

### Kim (2010) Compact Filter (Top Priority)

Helmholtz-type implicit filter κ_f: (I − α_f h² ∇²)f̂ = f. Sharper cutoff at intermediate wavenumbers than Lele.

## Conservation-Preserving Approaches

### Flux-Form Filtering

Apply filter to numerical flux, not state variable:
F_{i+½} = F̃_{i+½}^CCD − α(u_{i+1} − u_i)

Discrete conservation guaranteed: ΣΔu = Σ(F_{out} − F_{in}) = 0.

### Implicit Compact Filter on Fluxes

Apply Lele-type filter to face fluxes F_{i+½} rather than cell values u_i. Combines spectral sharpness with exact conservation.

### LES Approach

Smagorinsky-type subgrid viscosity ν_eff = (C_s Δ)² |S| provides physically motivated, locally adaptive dissipation. Often more effective than numerical filters for parasitic current suppression.

### Pressure Filtering: Forbidden

Never filter p directly (breaks ∇·u = 0). Instead filter ∇p or PPE RHS divergence.

## Geometric Filters (CCD-Native)

### h² Scaling (Critical Design Principle)

q* = q + C h² w(ψ) ∇²q (positive sign = diffusion)

CCD returns physical derivatives (units 1/L). Without h² scaling: C · ∇²q ~ C·q/h² → unstable. With h² scaling: C·h²·∇²q ~ C·q → mesh-independent.

**Stability (2D):** C < 1/8 = 0.125. Recommended: C = 0.03–0.08.

### Filter 1: Normal-Vector Diffusion (Priority 1)

n* = n + C h² ∇·(|∇φ| ∇n), then re-normalize n* ← n*/|n*|

Weight w = |∇φ| ≈ 1 (SDF). Interface-limited via δ_ε mask. CCD cost: 8 calls/component (2D).

### Filter 2: Interface-Limited κ Filter (Priority 2)

κ* = κ + C h² · 4ψ(1−ψ) · ∇²κ

Weight w = 4ψ(1−ψ) is O(1) and h-independent (unlike δ_ε = O(1/h)). CCD cost: zero if d2 pre-computed.

### Pipeline Integration

φ → ∇φ(CCD) → n → **[n filter]** → κ = −∇·n* → **[κ filter]** → CSF
