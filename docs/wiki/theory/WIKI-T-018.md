---
ref_id: WIKI-T-018
title: "Hermite Field Extension (HFE): O(h^6) Interface-Crossing Field Extension via CCD"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/appD4_gfm.tex
    git_hash: 3d4d1bb
    description: "HFE formulation: Extension PDE steady state, CCD Hermite interpolation, 2D tensor product"
consumers:
  - domain: L
    usage: "HFE module for split-PPE solver (future); currently CSF+HFE not used"
  - domain: A
    usage: "Appendix D.4 referenced from §8 (PPE), §9 (Balanced-Force)"
  - domain: E
    usage: "Curvature/HFE experiments (WIKI-E-002)"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-008]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## Motivation

CCD's 3-point stencil crossing the interface samples discontinuous pressure (Young-Laplace jump [p]_Γ = σκ), triggering Gibbs oscillation. HFE extends the source-phase field across the interface so CCD operates on smooth data everywhere.

**Current status:** Not needed for CSF + smoothed Heaviside solver (pressure is smooth). Required for future **split-PPE solver** where each phase has independent PPE with explicit pressure jump.

## Extension PDE Background

Aslam (2004): ∂q/∂τ + sgn(φ) n̂·∇q = 0

Steady state: ∇q · n̂ = 0 (zero normal gradient) — equivalent to nearest-point extension q_ext(x) = q(x_Γ(x)).

**HFE key insight:** Construct this steady state directly from CCD Hermite data (f, f', f'') without pseudotime iteration.

## Closest Point Computation

For target-side point x (φ(x) ≥ 0):

x_Γ = x − φ(x) n̂(x)

where n̂ = ∇φ/|∇φ| evaluated by CCD D^(1) at O(h⁶). Position accuracy: O(h⁶) when |∇φ| ≈ 1 (SDF condition).

## CCD Hermite 5th-Order Interpolation

From adjacent source-side points (x_a, x_b) with 6 data values (f, f', f'' at each), construct unique 5th-degree polynomial:

P(ξ) = Σ_{k=0}^5 c_k ξ^k, where ξ = (x−x_a)/h ∈ [0,1]

**Interpolation error:** |P(x)−f(x)| ≤ ||f⁶||_∞/6! · |(x−x_a)³(x−x_b)³| = O(h⁶)

Matches CCD differentiation accuracy.

**One-sided extrapolation:** When x_Γ falls outside last source cell, use 2 source-side points. Extrapolation distance ≤ h → |error| ∝ (2h)³·h³ = 8h⁶ → O(h⁶) maintained.

## 2D Extension: Tensor Product

Sequential interpolation: Hermite in x for each row → Hermite in y for result. Requires 4 CCD evaluations (q_x, q_xx, q_y, q_yy + mixed derivatives) vs 10 for pseudotime iteration.

## Comparison with Aslam (2004)

| | Aslam original | HFE (this work) |
|---|---|---|
| Method | 1st-order upwind + forward Euler | CCD Hermite direct construction |
| Accuracy | O(h) (numerical diffusion) | O(h⁶) |
| Iteration | Pseudotime (~5 sweeps) | None (direct) |
| Data required | f only | f, f', f'' (CCD native) |

## Algorithm Integration Points

1. **Pre-PPE (Step 5c):** Extend p^n → p^n_ext for IPC predictor ∇p^n term
2. **Pre-Corrector (Step 7):** Extend δp → δp_ext for velocity correction u^{n+1} = u* − (Δt/ρ)∇(δp_ext)

## Current Positioning

- CSF + smoothed Heaviside: HFE **not needed** (pressure already smooth)
- Split-PPE solver (ρ_l/ρ_g > 10): HFE **essential** — recommended upgrade path for high density ratio
