---
ref_id: WIKI-T-011
title: "CCD Coefficient Derivation: Interior O(h^6) and Boundary O(h^5)/O(h^4) Stencils"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/appendix_ccd_coef_s1.tex
    git_hash: 3d4d1bb
    description: "Interior CCD coefficients via Taylor expansion: Eq-I (α₁,a₁,b₁) and Eq-II (β₂,a₂,b₂)"
  - path: paper/sections/appendix_ccd_coef_s2.tex
    git_hash: 3d4d1bb
    description: "Boundary CCD coefficients: one-sided Eq-I (O(h^5)), Eq-II (O(h^2)→O(h^4) promotion)"
consumers:
  - domain: L
    usage: "ccd_solver.py implements these exact coefficients in block Thomas assembly"
  - domain: A
    usage: "Appendix B.1 referenced from §4 (CCD formulation)"
  - domain: E
    usage: "Convergence tests validate O(h^6) interior / O(h^4.8) boundary slopes"
depends_on:
  - "[[WIKI-T-001]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## Interior Coefficients (O(h^6))

### Equation-I (first derivative)

LHS: α₁ f'_{i-1} + f'_i + α₁ f'_{i+1}
RHS: a₁(f_{i+1}−f_{i-1})/(2h) + b₁(f''_{i+1}−f''_{i-1})h/2

Taylor expand LHS and RHS to O(h^6), match coefficients of f'_i, h²f'''_i, h⁴f⁵_i:

| Equation | Condition |
|----------|-----------|
| f'_i | 1 + 2α₁ = 2a₁ |
| h²f'''_i | α₁ = a₁/3 + 2b₁ |
| h⁴f⁵_i | α₁/12 = a₁/60 + b₁/3 |

**Solution:** α₁ = 7/16, a₁ = 15/16, b₁ = 1/16

**Truncation error:** TE_I = −(1/7!) h⁶ f⁷_i — same order as 7-point explicit stencil.

### Equation-II (second derivative)

LHS: β₂ f''_{i-1} + f''_i + β₂ f''_{i+1}
RHS: a₂(f_{i+1}−2f_i+f_{i-1})/h² + b₂(f'_{i+1}−f'_{i-1})/(2h)

Match coefficients of f''_i, h²f⁴_i, h⁴f⁶_i:

**Solution:** β₂ = −1/8, a₂ = 3, b₂ = −9/8

**Truncation error:** TE_II = −(1/20160) h⁶ f⁸_i = O(h⁶).

**Key insight:** 3-point stencil achieves 7-point equivalent accuracy via coupled (f',f'') unknowns.

## Boundary Coefficients

### Eq-I Boundary (left, i=0): O(h^5)

One-sided stencil with unknowns (α, β, c₀, c₁, c₂, c₃). Key constraints:
- β = −α (eliminate f''₀ from LHS)
- **α = 3/2 is the unique O(h^5) choice** (any other α gives only O(h^4))

Coefficients: α = 3/2, c₀ = −23/6, c₁ = 21/4, c₂ = −3/2, c₃ = 1/12.

### Eq-II Boundary (left, i=0): O(h^2) → O(h^4) promotion

**4-point formula (O(h^2)):** f''₀ = (2f₀ − 5f₁ + 4f₂ − f₃)/h²

**6-point formula (O(h^4)):** f''₀ = (45f₀ − 154f₁ + 214f₂ − 156f₃ + 61f₄ − 10f₅)/(12h²)

The 6-point promotion is used when n_pts ≥ 6; otherwise 4-point fallback. This removes the boundary bottleneck, yielding ~4.8 convergence slope in d2 tests.

Right boundary uses mirror formula: f₀→f_N, f₁→f_{N-1}, etc.
