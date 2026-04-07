---
ref_id: WIKI-T-023
title: "Surface Tension Semi-Implicit Method: Laplace-Beltrami Linearization (Future)"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: "docs/memo/将来_表面張力半陰解法の導入.md"
    git_hash: e62cd50
    description: "Semi-implicit surface tension via Laplace-Beltrami: benefits, risks, pseudotime solution"
consumers:
  - domain: L
    usage: "Future enhancement for capillary CFL relaxation"
  - domain: A
    usage: "Referenced in future work discussion"
depends_on:
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-014]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## Motivation

Explicit surface tension imposes capillary CFL: Δt ∝ h^{3/2} (see [[WIKI-T-014]]). Semi-implicit treatment relaxes this constraint.

## Approach: Laplace-Beltrami Linearization

Using κn = Δ_s x_s (differential geometry) and x_s^{n+1} ≈ x_s^n + u^{n+1}Δt:

(I − σΔt²/ρ · δ_s^n Δ_s^n) u^{n+1} = u* + Δt/ρ (σκ^n n^n δ_s^n)

Explicit part: f_σ^n evaluated with same CCD operators as PPE (balanced-force preserved).
Implicit part: linearized Laplace-Beltrami correction.

## Three Critical Risks

### 1. Balanced-Force Condition Collapse

Linearization/approximation of surface tension term breaks operator consistency with CCD-PPE → parasitic currents re-emerge even for static droplet.

### 2. Matrix Singularity

Implicit matrix defined only near interface → near-singular. CCD unknowns (f, f', f'') increase matrix size → condition number worsens → iterative solver convergence degrades.

### 3. Interface-Momentum Mismatch

After solving u^{n+1} implicitly, CLS reinitialization modifies interface → inconsistency between momentum and interface position → non-physical energy increase.

## Proposed Solution: Pseudotime Inner Iterations

### Delta-Form (Incremental)

f_σ^{n+1} = f_σ^n + Δt L_σ(u^{n+1}). Explicit term uses same CCD operator → balanced-force at rest.

### Inner Iteration

(u^{n+1,k+1} − u^{n+1,k})/Δτ + R(u^{n+1,k+1}) = 0

Each iteration k recomputes κ and CCD matrix from latest interface position. At convergence: linearization error eliminated, balanced-force and interface consistency simultaneously achieved.

### Narrow-Band Regularization

Restrict implicit matrix to interface vicinity; identity in far field → removes singularity, aids solver convergence.

## Status

**Not implemented.** Documented as future enhancement path for high-Weber-number and fine-scale problems where capillary CFL is prohibitive.
