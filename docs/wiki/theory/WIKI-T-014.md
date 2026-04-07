---
ref_id: WIKI-T-014
title: "Capillary CFL Constraint & ALE Grid Motion Effects"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/appendix_numerics_solver_s1.tex
    git_hash: 3d4d1bb
    description: "Capillary wave CFL derivation from dispersion relation; ALE effect analysis"
consumers:
  - domain: L
    usage: "Timestep controller uses Δt_σ formula for capillary CFL limit"
  - domain: A
    usage: "Appendix C.3 referenced from §6 (time integration, stability constraints)"
  - domain: E
    usage: "Timestep selection in all two-phase experiments"
depends_on:
  - "[[WIKI-T-003]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## Capillary Wave CFL Derivation

### Step 1: Dispersion Relation

Capillary wave linear stability: ω² = σ k³ / (ρ_l + ρ_g)

Phase velocity: c_σ = √(σk/(ρ_l+ρ_g)). Group velocity: c_g = (3/2) c_σ.

### Step 2: Maximum Resolvable Wavenumber

Nyquist: k_max = π/Δx.

### Step 3: CFL Application

c_g(k_max) Δt ≤ Δx gives:

**Δt_σ = √((ρ_l+ρ_g) Δx³ / (2πσ))**

Exact coefficient: 2/(3√π) ≈ 0.376; simplified form uses 1/√(2π) ≈ 0.399 (+6%, absorbed by safety factor C_σ < 1).

### Key Scaling

Δt_σ ∝ Δx^{3/2} — halving grid strengthens constraint by ~2.8×.

### Large Density Ratio Interpretation

For ρ_l/ρ_g = 1000 (water/air): ρ_l+ρ_g ≈ ρ_l. Gas inertia negligible (<0.1%). Surface tension = restoring force, liquid ρ_l = inertia. Density ratio 1000 allows ~32× larger Δt_σ than equal-density case.

## ALE Grid Motion (Not Implemented)

**ALE formulation:** ∂ψ/∂t + ∇·((u − v_mesh)ψ) = 0

**Error from omitting ALE:**

ε_ALE ~ |v_mesh| · |∇ψ| · Δt ~ U_Γ · (1/ε) · Δt

### Validity Conditions

| Condition | δ/h | ALE omission |
|---|---|---|
| Slow interface | < 0.1 | Good (error < 10% of Δt² term) |
| Standard | ≈ 0.5 | Conditional (verify grid convergence) |
| High-speed, ρ_l/ρ_g=1000 | > 1 | Accuracy degrades (ALE recommended) |

**Mode 1 (fixed grid, this work):** v_mesh=0, no ALE error, O(Δt²) preserved. Risk: resolution lost if interface moves far from initial refinement zone.

**Mode 2 (per-step regrid, no ALE):** Degrades to O(Δt) when δ/h > 1. ALE implementation strongly recommended for rising bubble benchmarks.
