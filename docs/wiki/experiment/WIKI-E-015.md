---
id: WIKI-E-015
title: "§13 Benchmark Suite: 3 Physical Validation Experiments (Pruned from 8)"
status: ACTIVE
created: 2026-04-10
updated: 2026-04-10
depends_on: [WIKI-E-008, WIKI-L-014, WIKI-X-007]
---

# §13 Benchmark Suite (Pruned)

## Pruning Rationale

Original 8 experiments were audited against §11–§12 coverage. **5 removed:**

| Removed | Reason |
|---------|--------|
| Static droplet (grid conv.) | Duplicates exp12_07 + exp12_16 + exp12_02 |
| RT instability σ>0 | σ=0 validated in exp12_12; σ>0 is linear superposition with capillary (§13.1) |
| Two-droplet collision | ρ=1000 PPE diverges (WIKI-E-008); no 2D coalescence reference |
| Two-bubble DKT | ρ=1000 unsupported; qualitative only, no quantitative 2D reference |
| 9-bubble swarm | No quantitative 2D swarm reference; demonstration, not validation |

**Key principle:** Each §13 experiment must provide (1) physics absent from §12, (2) quantitative reference solution, (3) feasible density ratio (ρ ≤ 10).

## 3 Retained Experiments

| §13 | Name | Reference | New physics vs §12 |
|------|------|-----------|-------------------|
| §13.1 | Capillary wave decay | Prosperetti 1981 | Oscillation frequency ω₀ + viscous decay β |
| §13.2 | Single rising bubble | Hysing et al. 2009 | Buoyancy-driven body motion |
| §13.3 | Taylor deformation | Taylor 1932 | Shear deformation D(Ca, λ) |

### §13.1: Capillary Wave — Prosperetti (1981)

- Perturbed circle r(θ) = R₀(1 + ε cos(2θ)), ε=0.05, R₀=0.25
- ρ_l=10, ρ_g=1, μ=0.05, σ=1.0; N=128
- **Not a duplicate of exp12_15:** that measures Δt_σ stability limit; this measures physical ω₀ and β
- Analytical: ω₀² = l(l−1)(l+2)σ / [(ρ_l+ρ_g)R₀³] ≈ 46.5 → ω₀ ≈ 6.82
- Criterion: period error <10%, decay rate error <20%

### §13.2: Rising Bubble — Hysing (2009)

- Re=35, Eo=10, ρ_l/ρ_g=10 (modified from Hysing's 1000)
- σ=0.225, μ=0.101 (derived from Re, Eo)
- **Not a duplicate of exp12_12 (RT):** RT = interfacial instability; this = individual body dynamics
- Metrics: centroid y_c(t), rise velocity v_c(t), circularity C(t)
- Criterion: |ΔV|/V₀ < 0.5%

### §13.3: Taylor Deformation — Taylor (1932)

- Neutrally buoyant (ρ_l=ρ_g=1), Couette shear γ̇=2.0
- Ca ∈ {0.1, 0.2, 0.3, 0.4} × λ ∈ {1, 5} (8 cases)
- **Unique:** isolates σ+μ coupling (no gravity); tests variable viscosity μ(ψ)
- Analytical: D = (19λ+16)/(16λ+16) × Ca
- Criterion: |D_sim−D_th|/D_th < 10% for Ca ≤ 0.3

## §12 → §13 Progression

| Aspect | §12 (consistency) | §13 (validation) |
|--------|--------------------|-------------------|
| Physics | Manufactured/self-consistent | Published benchmarks |
| σ role | CFL limit (exp12_15) | Restoring force (§13.1), shape control (§13.2–3) |
| Gravity | Static (exp12_01) or instability (exp12_12) | Body motion (§13.2) |
| Viscosity | Uniform | Variable μ(ψ) tested (§13.3) |
| Reference | Analytical MMS | Prosperetti, Hysing, Taylor |
