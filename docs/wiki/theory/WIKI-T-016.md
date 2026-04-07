---
ref_id: WIKI-T-016
title: "CCD Pseudotime Implicit Method: Initial Pressure, Sweep Iteration, Splitting Error"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/appendix_ppe_pseudotime.tex
    git_hash: 3d4d1bb
    description: "CCD implicit pseudotime PPE solver: formulation, sweep factorization, splitting error analysis"
consumers:
  - domain: L
    usage: "PPESolverSweep implements the pseudotime iteration with CCD block Thomas"
  - domain: A
    usage: "Appendix D.2 (formerly §8.4) referenced from §8 (pressure solver)"
  - domain: E
    usage: "PPE solver benchmarks use this method; Δτ_opt from [[WIKI-T-015]]"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-005]]"
  - "[[WIKI-T-015]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## Initial Pressure p⁰ Setup

Three options for IPC predictor at n=0:
1. **Static droplet (verification):** Analytic Young-Laplace p⁰ = σ/R (liquid), 0 (gas)
2. **General (recommended):** Solve PPE once from p⁰=0 at n=0 (one extra solve cost)
3. **Simple:** p⁰=0, transient O(Δt) error for first few steps; acceptable for most problems

## Pseudotime Formulation

Transform elliptic PPE L_h(δp) = q_h into parabolic relaxation:

∂(δp)/∂τ = q_h − L_h(δp)

Implicit Euler in τ: (I + Δτ L_h)(δp)^{m+1} = (δp)^m + Δτ q_h

**Unconditionally stable** — no CFL restriction on Δτ.

## Two Implementation Approaches

### Approach 1: Sweep (matrix-free, this section)

Factor: (I + Δτ L_x)(I + Δτ L_y)(δp)^{m+1} ≈ (δp)^m + Δτ q_h

Each factor solved by CCD block Thomas in O(N) per line. Total per iteration: O(N²).

**Splitting error:** Δτ² L_x L_y(δp)^{m+1} — converged solution satisfies L_h(δp) + Δτ L_x L_y(δp) = q_h, not L_h(δp) = q_h exactly. Set ε_tol above splitting floor.

### Approach 2: Krylov (LGMRES/direct LU)

Kronecker product global matrix (see [[WIKI-T-012]]). No splitting error. Better for debugging/verification but O(N³) assembly.

## Solver Comparison

| Method | Spatial order | Matrix-free | Splitting error | Use case |
|---|---|---|---|---|
| CCD pseudotime sweep | O(h⁶) | Yes | O(Δτ²) | Large grids (N ≥ 128) |
| CCD Kronecker + LGMRES | O(h⁶) | No | None | Verification, small grids |
| FVM BiCGSTAB | O(h²) | No | None | Low-order alternative |

## Convergence Control

- Residual: ε^m = ||L_h(δp)^m − q_h||
- Stop when ε^m < ε_tol
- Warm start: use previous timestep solution as initial guess
- Gauge pin at center node (N/2, N/2) for Neumann BC zero-space removal
