---
ref_id: WIKI-T-020
title: "Curvature Invariance Theorem: ψ-Based Computation Eliminates Logit Inversion"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: "docs/memo/理論_擬似ヘヴィサイド関数の構造情報を活用した Conservative Level Set 法の高精度界面曲率計算法の提案.md"
    git_hash: e62cd50
    description: "Curvature invariance theorem proof, ψ-direct formula, chain-rule verification, CCD synergy"
consumers:
  - domain: L
    usage: "CurvatureCalculator can use ψ directly instead of φ — eliminates logit inversion"
  - domain: A
    usage: "Theoretical justification for ψ-direct curvature in §3 and §4"
depends_on:
  - "[[WIKI-T-007]]"
  - "[[WIKI-T-008]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## Theorem: Level-Set Curvature is Monotone-Transformation Invariant

Let ψ = g(φ) with g ∈ C², g' > 0 (strictly monotone increasing). Then:

**−∇·(∇ψ/|∇ψ|) = −∇·(∇φ/|∇φ|) = κ**

**Proof:** ∇ψ = g'(φ)∇φ. Since g'>0: |∇ψ| = g'(φ)|∇φ|. Therefore n̂_ψ = ∇ψ/|∇ψ| = ∇φ/|∇φ| = n̂_φ. Since n̂_ψ = n̂_φ, κ = −∇·n̂ is identical regardless of which variable is used. QED.

**Corollary:** H_ε(φ) = 1/(1+e^{-φ/ε}) is strictly monotone increasing → **logit inversion is completely unnecessary for curvature computation.**

**2026-04-26 discrete caveat:** The corollary is exact in the continuum. It
does not prove that a discrete `psi`-direct curvature operator is
energy-stable, balanced-force compatible, or a discrete surface-area gradient.
The ch13 capillary redesign therefore treats `psi`-direct curvature as one
candidate geometry operator, not as a production guarantee; see [[WIKI-T-077]].

## 2D Curvature Formula (ψ-Direct)

κ = −(ψ_y² ψ_{xx} − 2ψ_x ψ_y ψ_{xy} + ψ_x² ψ_{yy}) / (ψ_x² + ψ_y²)^{3/2}

Mathematically identical to the φ-based formula — not an approximation.

## Chain-Rule Verification

Substituting φ derivatives via H' = (1/ε)ψ(1−ψ), H'' = (1/ε²)ψ(1−ψ)(1−2ψ):

The H'' coefficient in the numerator is ψ_x²ψ_y² − 2ψ_x²ψ_y² + ψ_x²ψ_y² = **0** (exact cancellation). The H'^3 factors cancel between numerator and denominator. Confirms invariance theorem algebraically.

## CCD Synergy

CCD simultaneously returns (ψ, ψ', ψ'') at O(h⁶). All inputs for the ψ-direct curvature formula are available at zero extra cost.

## Advantages over ψ→φ→κ Pipeline

1. **Eliminates logit inversion entirely** — no saturation-domain singularity (ln(ψ/(1−ψ)) blows up as ψ→0,1)
2. **Preserves ψ's smooth structure** — no destruction by point-wise nonlinear transform
3. **Eikonal condition |∇φ|≈1 no longer a prerequisite** for curvature accuracy

## Implementation: Hybrid Strategy

- Interface vicinity (ψ_min < ψ < 1−ψ_min, ψ_min=0.01): use ψ-direct formula (safe, denominator > 0)
- Far from interface (ψ→0 or 1): |∇ψ|→0 causes zero-division; use φ-based or set κ=0 (curvature irrelevant there)
