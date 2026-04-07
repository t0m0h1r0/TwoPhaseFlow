---
ref_id: WIKI-T-017
title: "FVM Reference Methods: PPE Face Coefficients, CSF Model, Rhie-Chow & Balanced-Force Accuracy"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/appendix_numerics_solver_s4.tex
    git_hash: 3d4d1bb
    description: "FVM PPE face coefficients, CSF complete formulation, Rhie-Chow, Balanced-Force Taylor analysis"
consumers:
  - domain: L
    usage: "FVM PPE matrix assembly; RC correction formula; BF operator matching"
  - domain: A
    usage: "Appendix D.3 referenced from §7 (RC), §8 (PPE), §9 (BF)"
  - domain: E
    usage: "Static droplet benchmark validates BF condition"
depends_on:
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-005]]"
  - "[[WIKI-T-009]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## PPE Face Coefficient: Harmonic Mean

For FVM discretization of ∇·(a∇p) where a = 1/ρ:

**a_f = 2/(ρ_L + ρ_R)** (harmonic mean of 1/ρ)

Derivation: series resistance integral ∫dx/a(x) = Δx/(2a_L) + Δx/(2a_R) → a_f = 2a_La_R/(a_L+a_R).

**Common implementation mistake:** ρ harmonic mean inverse (ρ_L+ρ_R)/(2ρ_Lρ_R) ≠ 2/(ρ_L+ρ_R).

Note: This work uses CCD product-rule expansion (O(h⁶)), not FVM. The face coefficient is the low-order limit.

### Periodic BC for FVM PPE

Three modifications: (1) wrap face a_{N-½} = 2/(ρ_{N-1}+ρ_0); (2) no half-cell volume correction; (3) ghost node identity constraint p_ghost − p_src = 0. ILU(0) preconditioning fails — use fill_factor=10.

## CSF Model: Complete Formulation

**Surface tension body force:**

f_σ = σκ n̂ δ_s ≈ σκ (∇ψ/|∇ψ|) |∇ψ| = σκ ∇ψ

Valid when |∇φ| ≈ 1 (Eikonal condition, maintained by CLS reinitialization).

**Young-Laplace verification:** In equilibrium ∇p = σκ∇ψ. Integrating across interface in normal direction:

p_gas − p_liq = σκ ∫ (∂ψ/∂s) ds = σκ(1−0) = σκ. QED.

## Rhie-Chow Correction

**Face velocity:**

u_f = ū_f − Δt(1/ρ)^harm_f [(∇p^n)_f − (∇p^n)_f̄]

Key interpolations:
- **Velocity ū_f:** arithmetic mean (physically continuous)
- **Density coefficient d_f:** 1/ρ harmonic mean = 2/(ρ_L+ρ_R) (flux continuity / series resistance)

**Detection mechanism:** Checkerboard pressure gives large face gradient (p_E−p_P)/Δx but near-zero cell-center average → correction damps oscillation.

### RC Divergence (PPE RHS)

(∇_h^RC · u*)_{i,j} = [(u_f)_{i+½,j} − (u_f)_{i-½,j}]/Δx + [(v_f)_{i,j+½} − (v_f)_{i,j-½}]/Δy

**Must use face-velocity divergence** for PPE RHS. Cell-center divergence causes checkerboard backflow.

Note: In CSF+HFE+DCCD formulation, DCCD filter handles checkerboard and RC correction is not needed.

### Balanced-Force Extension

u_f = ū_f − Δt(1/ρ)^harm_f [(∇p^n)_f − (∇p^n)_f̄ − ((f_σ)_f − (f_σ)_f̄)]

Surface tension terms cancel at equilibrium: (∇p)_f ≈ (f_σ)_f at face level.

## Balanced-Force Operator Mismatch Analysis

### Mixed-operator error (FD + CCD)

D_CCD p − (κ/We) D_FD ψ = 0 + O(h⁶) − (κ/We)O(h²) = **O(h²)** → drives parasitic currents → blowup

### Same-operator (CCD + CCD)

D_CCD p − (κ/We) D_CCD ψ = O(h⁶) → parasitic current discretization error reduced to O(h⁶)

### But CSF model error dominates

Practical parasitic current convergence: **O(h²)** due to CSF interface thickness ε ~ O(h).

"Balanced-Force" cancels **discretization error** (to O(h⁶)), not **CSF model error** (O(ε²) ≈ O(h²)).
