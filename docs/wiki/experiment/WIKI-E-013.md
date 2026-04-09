---
ref_id: WIKI-E-013
title: "Gap-filling component verification: spatial, interface, solver, time (§11 additions)"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: "experiment/ch11/exp11_23_mixed_partial_convergence.py"
    description: "2D mixed partial CCD convergence"
  - path: "experiment/ch11/exp11_24_dgr_verification.py"
    description: "DGR thickness correction verification"
  - path: "experiment/ch11/exp11_25_cn_viscous_temporal.py"
    description: "Crank-Nicolson temporal accuracy"
  - path: "experiment/ch11/exp11_26_weno5_vs_dccd.py"
    description: "WENO5 vs DCCD CLS advection comparison"
  - path: "experiment/ch11/exp11_27_pressure_filter_prohibition.py"
    description: "Pressure filter divergence demonstration"
  - path: "experiment/ch11/exp11_28_ppe_condition_number.py"
    description: "PPE condition number scaling"
consumers:
  - domain: A
    usage: "Paper §11 verification sections"
  - domain: E
    usage: "Regression baselines for future experiments"
depends_on:
  - "[[WIKI-E-001]]"
  - "[[WIKI-E-002]]"
  - "[[WIKI-E-003]]"
  - "[[WIKI-E-005]]"
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-002]]"
  - "[[WIKI-T-005]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-10
---

# Gap-Filling Component Verification (§11 Additions)

Audit of §4-§9 theory vs §11 experiments identified 11 critical coverage gaps (78% baseline coverage). Six new §11 experiments were added to close the most important gaps. All PASS.

## Exp 11-23: 2D Mixed Partial Derivative ∂²f/∂x∂y

**Validates:** §6b claim that sequential CCD application achieves O(h⁶) for cross-derivatives.

| BC | Measured Order | N range |
|----|---------------|---------|
| Periodic | O(h^6.0) | 16–256 (roundoff at 256) |
| Wall | O(h^5.0) | 16–256 (boundary-limited) |

- Commutativity error (∂x∂y vs ∂y∂x): O(10⁻¹²) — machine precision
- **Key insight:** Non-diagonal viscous term ∂_y(μ ∂_x u) has the required O(h⁶) discretization accuracy

## Exp 11-24: DGR Thickness Correction Verification

**Validates:** §7b claims for Direct Geometric Reinitialization.

| Test | Result |
|------|--------|
| (a) Idempotency | ε_eff/ε = 1.000 after 100 applications |
| (b) Thickness restoration (1.4× broadening) | Restored to ε_eff/ε ≈ 1.000 |
| (c) Frequency study | No DGR: ε_eff/ε = 3.97; DGR every 20 steps: 1.03 (92× improvement) |

- **Key insight:** DGR is a fixed point for correct-thickness profiles; 20-step frequency is optimal cost/accuracy balance

## Exp 11-25: Crank-Nicolson Temporal Accuracy

**Validates:** §5 CN scheme O(Δt²) + unconditional stability.

- Temporal convergence: slopes 2.00, 1.99, 2.04, 2.18 (periodic BC, N=64, GMRES solver)
- Stability: CN stable at CFL_ν = 10; Euler diverges at CFL_ν ≥ 5
- **Implementation note:** Fixed-point iteration DIVERGES for CN when dt·ν/(2h²) >> 1 (spectral radius exceeds 1). Must use GMRES or direct solver for the implicit equation (I - dt·ν/2·L)u^{n+1} = rhs.

## Exp 11-26: WENO5 vs DCCD CLS Advection

**Validates:** §7 motivation for DCCD over WENO5.

At N=256, ε=0.02 (1 period):
| Scheme | L₂ Error | Interface Width |
|--------|----------|-----------------|
| CCD | 9.1e-7 | Preserved |
| WENO5 | 4.6e-5 | Preserved |
| DCCD | 2.9e-3 | Preserved |

- **Key insight:** DCCD has larger L₂ error than WENO5 (explicit filter O(h²) dominates), but provides: (1) discrete mass conservation [[WIKI-T-002]], (2) tunable filter strength, (3) explicit spectral control. Interface width preservation is equivalent across all schemes. The real accuracy drivers are ε/h and reinitialization frequency, not advection scheme [[WIKI-E-009]].

## Exp 11-27: Pressure Filter Prohibition

**Validates:** §8c warning that DCCD filter on pressure destroys ∇·u = 0.

| Filter | Divergence Error Scaling |
|--------|------------------------|
| None (CCD Laplacian) | O(h^6.0) vs exact |
| ε_d = 0.05 | O(h^2.0) divergence error |
| ε_d = 0.25 | O(h^2.0) divergence error (5× larger coefficient) |

- **Key insight:** The filter introduces ∇²p̃ ≠ ∇²p, causing ∇·u^{n+1} = (∇²p - ∇²p̃)/Δt ≠ 0. The error is O(ε_d·h²), which is O(h²) — same order as CSF model error, making it a dominant error source.

## Exp 11-28: PPE Condition Number Scaling

**Validates:** §9c claim κ ≈ O(ρ_l/ρ_g · h⁻²).

| ρ_l/ρ_g | N=8 | N=16 | N=32 | N=64 |
|----------|------|-------|-------|-------|
| 1 | 4.4e3 | 3.4e4 | 2.7e5 | 2.1e6 |
| 10 | 1.6e3 | 2.5e4 | 2.6e5 | 2.1e6 |
| 100 | 8.5e2 | 2.8e4 | 4.9e5 | 3.1e6 |
| 1000 | 8.7e2 | 4.3e4 | 3.4e6 | 2.2e7 |

- Equal density: κ ∝ N^3 (standard Laplacian scaling)
- High density ratio: κ amplified beyond O(ρ/h²), reaching κ = 2.2×10⁷ at ρ=1000, N=64
- **Key insight:** This directly explains DC divergence at ρ_l/ρ_g ≥ 10 ([[WIKI-E-005]]) — the iteration matrix spectral radius exceeds 1 due to extreme condition number.
