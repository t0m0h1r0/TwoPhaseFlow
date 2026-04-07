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

## Recommended Path for High Density Ratio

DC+LU stalls at ρ_l/ρ_g ≥ 5. GMRES with FD preconditioner avoids ∇ρ mismatch issue and is the natural 3D extension. Requires sparse matrix assembly but avoids splitting error.
