---
ref_id: WIKI-T-024
title: "CCD-PPE Solver Convergence: DC+LU Results, ADI Failure, and Alternative Candidates"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: "docs/memo/理論_CCD-PPEソルバ収束解析_総括.md"
    git_hash: e62cd50
    description: "CCD-PPE solver summary: DC spectral analysis, ADI failure, DC+ω experimental results"
  - path: "docs/memo/理論_CCD代替ソルバ候補.md"
    git_hash: e62cd50
    description: "Alternative solver candidates: ADI, multigrid, GMRES+FD-prec theoretical comparison"
  - path: docs/memo/dccd_ppe_investigation.md
    git_hash: e62cd50
    description: "DCCD PPE investigation: defect correction with FD preconditioner failure analysis"
  - path: docs/memo/filter_stabilization_dc_ccd_ppe.md
    git_hash: e62cd50
    description: "Filter stabilization of DC-CCD PPE: experimental study of iteration failure modes"
consumers:
  - domain: L
    usage: "PPE solver selection and parameter tuning"
  - domain: A
    usage: "§8 solver discussion, appendix D.1 convergence theory"
depends_on:
  - "[[WIKI-T-005]]"
  - "[[WIKI-T-015]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## Summary of Findings

### DC+LU (Chosen Method)

Defect correction with direct LU solve (spsolve) for FD preconditioner system. ω-relaxation required.

**Experimental results (exp10_18):**

| N | ρ_l/ρ_g | ω=0.30 | ω=0.50 | ω=0.70 | ω=0.83 |
|---|---------|--------|--------|--------|--------|
| 32 | 1 | 72 itr ✓ | 38 ✓ | 22 ✓ | 109 stall |
| 64 | 1 | 72 ✓ | 37 ✓ | 22 ✓ | 140 stall |
| 64 | 2 | 74 ✓ | 39 ✓ | 23 ✓ | 142 stall |
| 64 | ≥5 | stall | stall | stall | stall |

**k=3 iterations suffice for O(h⁶)** (direct LU in Step 2 gives exact FD solve → fast effective damping).

### ADI (Rejected)

CCD-ADI factorizes as (I+ΔτL_x)(I+ΔτL_y)p = rhs. Splitting error Δτ²L_xL_y limits convergence to **O(h⁴)** regardless of iteration count → cannot achieve O(h⁶). Confirmed experimentally (exp10_17).

### Variable-Density Stall Mechanism

Interface CCD (O(h⁶)) vs FD (O(h²)) ∇ρ discretization creates residual floor ∝ (ρ_l/ρ_g − 1)·O(h²). At ρ_l/ρ_g ≥ 5 and N=64: floor exceeds tolerance → stall.

### ω=0.1 Pathology

Even at uniform density: smooth-mode convergence rate 0.9/iteration → ~230 iterations needed. CCD discretization error floor ~3×10⁻⁸ reached before tolerance.

## Alternative Solver Candidates

| Solver | Spatial order | Variable density | Practical status |
|--------|-------------|-----------------|-----------------|
| DC+LU (ω=0.5) | O(h⁶), k=3 | ρ_l/ρ_g ≤ 2 | **Implemented, chosen** |
| Pseudotime sweep | O(h⁶) at convergence | Limited (splitting error) | Implemented, backup |
| LGMRES + Kronecker | O(h⁶) | Moderate | Implemented, verification |
| GMRES + FD-prec | O(h⁶) target | High density ratio path | **3D upgrade path** |
| Multigrid + CCD | O(h⁶) target | Unknown | Not investigated |

### Picard Density-Gradient Splitting (Rejected — exp11_14, 2026-04-08)

**Idea**: Split L_H = A − B where A = (1/ρ)Δ (Laplacian-only), B = (1/ρ²)(∇ρ·∇) (coupling). Outer Picard iteration: A p^{k+1} = q + B p^{k}. Inner DC+LU solves A p = f — no ∇ρ term → eigenvalue ratio [1, 2.4] regardless of density ratio → inner DC always converges.

**Result**: Inner DC converges as predicted, but **outer Picard diverges at all ρ_l/ρ_g ≥ 2**. The coupling term B is NOT a small perturbation — its spectral radius ‖A⁻¹B‖ ≈ |∇ρ|/(ρ·k_min) = O(Δρ/(ε·ρ·π)) exceeds 1 at the lowest Fourier mode when the density jump is large. Under-relaxation β < 1 helps marginally but cannot overcome O(1/h) amplification.

| ρ_l/ρ_g | baseline DC (ω=0.5) | Picard-DC (best β) |
|---------|---------------------|-------------------|
| 1 | 38 evals ✓ | 66 evals ✓ (β=1.0) — slower |
| 2 | stall (N=32) | stall — worse than baseline |
| ≥5 | stall | stall (higher residual floor) |

**Lesson**: Density-gradient splitting is invalid when ∇ρ·∇p is a leading-order term (sharp interface). Only methods that handle the FULL operator L_H without splitting (Krylov, direct) can succeed at high density ratios.

### GMRES + FD-LU Preconditioner (exp11_15, 2026-04-08)

**Idea**: Use GMRES with L_FD^{-1} (spsolve) as preconditioner. CCD operator eval_LH serves as matrix-free matvec. Eigenvalue clustering in [α_min, α_max] should give fast convergence.

**Result**: GMRES hits the **same residual floor** as DC at all density ratios.

| N | ρ_l/ρ_g | DC res floor | GMRES res floor | Observation |
|---|---------|-------------|-----------------|-------------|
| 64 | 1 | 9.8e-9 ✓ | 6.7e-9 ✓ | Both converge |
| 64 | 2 | 8.4e-9 ✓ | 4.4e-9 ✓ | **GMRES 30% faster** (27 vs 39 evals) |
| 64 | 5 | 2.7e-8 stall | 3.2e-8 stall | Same floor |
| 64 | 1000 | 1.2e-4 stall | 1.8e-4 stall | Same floor |

**Diagnosis**: The stagnation floor is NOT a solver convergence issue — it's a **formulation-level numerical error**. At the interface, ∇ρ = O(Δρ/ε) = O((ρ_l−ρ_g)/h) amplifies the floating-point evaluation error of CCD-based (1/ρ²)(∇ρ·∇p), creating an irreducible residual floor ∝ (ρ_l/ρ_g)·h². No iterative solver (DC, GMRES, BiCGSTAB, etc.) can break this floor because the OPERATOR EVALUATION itself is the bottleneck.

**Positive finding**: At moderate density ratios (ρ_l/ρ_g = 2, N=64), GMRES converges 30% faster than DC (27 vs 39 evals) — the Krylov polynomial acceleration does help when the floor is below tolerance.

## Recommended Path for High Density Ratio

The stagnation floor is a formulation problem, not a solver problem. Solutions must eliminate ∇ρ from the operator:

1. **GFM (Ghost Fluid Method)**: Sharp interface → ρ piecewise constant → ∇ρ = 0 in each phase. Jump condition handles the interface. Eliminates the residual floor entirely.
2. **Kronecker direct solve**: Assemble full CCD operator as sparse matrix, solve directly with LU. No residual evaluation → no floor. Already documented in app:ccd_kronecker. Cost: O(n^{1.5}).
3. **Hybrid**: GFM for high density ratio + DC for moderate ratio (ρ_l/ρ_g ≤ 2).
