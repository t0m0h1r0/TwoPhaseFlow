---
ref_id: WIKI-T-022
title: "Extension PDE × CCD: Interface-Crossing Field Continuation and Limitations"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: docs/memo/extension_pde_ccd.md
    git_hash: e62cd50
    description: "Extension PDE theory, CCD integration, GFM+CCD failure analysis, comparison with CSF"
  - path: docs/memo/closest_point_hermite_extension.md
    git_hash: e62cd50
    description: "Direct Hermite interpolation as O(h⁶) alternative to Extension PDE iteration"
consumers:
  - domain: L
    usage: "HFE module design informed by these findings"
  - domain: A
    usage: "Appendix D.4 (HFE) and split-PPE discussion"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-018]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## CCD's Fundamental Constraint

CCD requires C^∞ (smooth) input fields. When the stencil crosses interface Γ where the field is discontinuous, Gibbs oscillation occurs and accuracy collapses.

## Interface Method Comparison

| Method | Interface representation | CCD compatibility | Near-interface accuracy | Issue |
|--------|------------------------|-------------------|------------------------|-------|
| CSF | Regularized δ_ε | Good (field smooth) | O(ε²) ≈ O(h²) | Model error rate-limiting |
| GFM | Discontinuous [p]=σκ | Fails (stencil breakdown) | O(h²)† | CCD operator indefinite |

†GFM+CCD experimental result: product-rule PPE operator has positive eigenvalues (boundary stencil asymmetry) → LGMRES diverges, pressure sign inverts. Direct LU gives correct sign but amplitude diverges O(h⁻²).

## Extension PDE: Making CCD-Compatible Fields

∂q/∂τ + sgn(φ) n̂·∇q = 0 (Aslam 2004)

Steady state: ∇q·n̂ = 0 → nearest-point extension. Source-phase values propagated to target phase along interface normals.

## Two Implementation Strategies

### Strategy A: Pseudotime Iteration (Aslam original)

1st-order upwind + forward Euler. Simple but O(h) accuracy due to numerical diffusion. Requires ~5 sweeps per field.

### Strategy B: Direct Hermite Construction (HFE — this work)

CCD provides (f, f', f'') at each grid point → 5th-degree Hermite polynomial from 2 source-side points → O(h⁶) interpolation at closest point. No iteration needed.

**Key advantages:** O(h⁶) vs O(h) accuracy; 4 CCD calls vs 10 sweeps in 2D; deterministic (no convergence criterion).

## Closest-Point Computation

x_Γ = x − φ(x) n̂(x), where n̂ computed by CCD D^(1) at O(h⁶). Position accuracy: O(h⁶) under Eikonal |∇φ|≈1.

## 2D Tensor Product

Sequential x-then-y Hermite interpolation. Mixed derivatives (q_{xy}, q_{xyy}) needed — computed by 2-stage CCD.

## Current Status

HFE is the chosen implementation ([[WIKI-T-018]]). Extension PDE iteration abandoned due to low accuracy. GFM+CCD path abandoned due to operator definiteness failure.
