---
ref_id: WIKI-T-010
title: "Interface Mathematical Proofs: Newton Convergence, Eikonal Precision, CLS Fixed-Point"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/appendix_interface_s1.tex
    git_hash: 3d4d1bb
    description: "ψ→φ Newton inversion quadratic convergence proof (saturation domain)"
  - path: paper/sections/appendix_interface_s2.tex
    git_hash: 3d4d1bb
    description: "One-Fluid derivation: 1D diffusion, δ-function absorption, viscosity interpolation"
  - path: paper/sections/appendix_interface_s4.tex
    git_hash: 3d4d1bb
    description: "|∇ψ|≈δ_s precision: O(ε²) error under Eikonal condition"
  - path: paper/sections/appendix_interface_s5.tex
    git_hash: 3d4d1bb
    description: "CLS reinitialization fixed-point proof and design rationale"
consumers:
  - domain: L
    usage: "Newton inversion in CLS module; clamping strategy justified here"
  - domain: A
    usage: "Appendix A referenced from §2 (One-Fluid), §3 (CLS, curvature)"
  - domain: E
    usage: "Convergence order expectations for interface-related experiments"
depends_on:
  - "[[WIKI-T-006]]"
  - "[[WIKI-T-007]]"
  - "[[WIKI-T-008]]"
  - "[[WIKI-T-009]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## A.1 — ψ→φ Newton Inversion: Quadratic Convergence

**Problem:** Invert ψ = H_ε(φ) to recover φ. Analytic logit φ = ε ln(ψ/(1−ψ)) works for most points; Newton iteration needed only in **saturation domain** (ψ→0 or ψ→1, i.e., > 15ε from interface — O(e^{-15}) fraction of grid).

**Key result:** Under clamping |φ| ≤ φ_max = 15ε, Newton converges quadratically:

|e_{k+1}| ≤ C |e_k|²

where C = ||F''||_∞ / (2 F'_min) < ∞. Bounds:
- F'(φ) = H_ε'(φ) > 0 always (F'_min > 0 in bounded interval)
- ||F''||_∞ ≤ 1/(4ε²)

**Practical implication:** Saturation points are O(e^{-15}) of total — negligible cost, no curvature contribution.

## A.2 — One-Fluid Formulation: Mathematical Mechanism

**1D demonstration:** Two-fluid diffusion (μ_l left, μ_g right) with jump conditions at x=0 is equivalent to single equation:

d/dx(μ(x) du/dx) = f_σ δ(x)

Integration over (-ε, +ε) recovers stress jump condition automatically. The δ-function absorbs interface conditions into the volume equation.

**Viscosity interpolation (CLS):** For linear ψ (Eikonal regime), FVM face viscosity is exactly the **arithmetic mean**:

μ_f = (μ_L + μ_R) / 2

derived from volume averaging of μ(ψ) = μ_l + (μ_g − μ_l)ψ.

Contrast: PPE coefficient 1/ρ uses **harmonic mean** a_f = 2/(ρ_L + ρ_R) from flux continuity (series resistance).

## A.3 — |∇ψ| ≈ δ_s Precision: O(ε²) under Eikonal

**Setup:** Under |∇φ| = 1, evaluate error of CSF approximation |∇ψ| ≈ δ_s via normal coordinate expansion.

**Key steps:**
1. Volume element in normal coordinates: dV = (1 − κ₁s)(1 − κ₂s) ds dA_Γ
2. First-order curvature term vanishes: ∫ s δ_ε(s) ds = 0 (δ_ε is even, s is odd)
3. Leading error from s² term: ∫ s² δ_ε(s) ds = π²ε²/3

**Result:**

∫_Ω f |∇ψ| dV − ∫_Γ f dA_Γ = O(ε² κ²)

For flat interface (κ=0): exact. With ε ~ Δx: error is O(Δx²). This is the CSF accuracy bottleneck (see [[WIKI-T-009]]).

## A.4 — CLS Reinitialization: Design Rationale and Fixed-Point Proof

**Design principle (reverse engineering):** Find A(ψ), B(ψ') such that steady state of ∂ψ/∂τ + ∇·[A(ψ) n̂] = ∇·[B(ψ')] yields ψ = H_ε(φ).

Target: ψ' = (1/ε) ψ(1−ψ). This uniquely determines A(ψ) = ψ(1−ψ), B = ε∇ψ, giving:

∂_τ ψ + ∇·(ψ(1−ψ) n̂) = ∇·(ε ∇ψ)

**Fixed-point proof (1D):** For ψ = H_ε(s) = 1/(1+e^{-s/ε}):
- LHS: d/ds[ψ(1−ψ)] = (1−2ψ) · (1/ε) ψ(1−ψ)
- RHS: ε ψ'' = (1−2ψ) · (1/ε) ψ(1−ψ) (independently derived via chain rule)
- LHS = RHS. No circular reasoning.

**Multi-D extension:** For κ ≠ 0, additional term is O(εκ ψ(1−ψ)) → vanishes as ε→0.
