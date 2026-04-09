---
ref_id: WIKI-X-007
title: "CFL constraint hierarchy and stability budget for two-phase CCD-PPE solver"
domain: X
status: ACTIVE
superseded_by: null
sources:
  - path: "paper/sections/10_full_algorithm.tex"
    description: "§10 full algorithm with CFL control (Step 0)"
  - path: "paper/sections/05_time_integration.tex"
    description: "§5 time integration schemes and CFL analysis"
  - path: "paper/sections/07b_reinitialization.tex"
    description: "§7b capillary CFL derivation"
  - path: "experiment/ch12/exp12_14_cross_viscous_cfl.py"
    description: "Cross-viscous CFL verification"
  - path: "experiment/ch12/exp12_15_capillary_cfl.py"
    description: "Capillary CFL verification"
consumers:
  - domain: L
    usage: "CFL condition implementation in time-stepping module"
  - domain: E
    usage: "Time-step selection for all simulations"
  - domain: A
    usage: "§10 algorithm description and §12 verification"
depends_on:
  - "[[WIKI-T-014]]"
  - "[[WIKI-E-014]]"
  - "[[WIKI-E-005]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-10
---

# CFL Constraint Hierarchy and Stability Budget

## Three Independent CFL Constraints

The two-phase CCD-PPE solver has three independent stability constraints on Δt. The effective time step is:

```
Δt = C_CFL × min(Δt_adv, Δt_σ, Δt_cross)
```

where C_CFL = 0.45 (§10 Step 0).

### 1. Advective CFL (loosest for typical flows)

```
Δt_adv = 1 / (|u|_max/Δx + |v|_max/Δy)
```

- Standard courant condition for TVD-RK3 + DCCD
- Formal stability limit: σ_max = √3/1.9 ≈ 0.91 (von Neumann analysis, §7)
- Typically O(h/U) — loosest constraint when U is moderate

### 2. Capillary CFL (tightest at fine grids)

```
Δt_σ = √((ρ_l + ρ_g) · Δx³ / (2πσ))
```

- Scaling: **Δt_σ ∝ Δx^{3/2}** (verified: exponent 1.505 ± 0.005)
- CCD-discretized stability limit: **40% of theoretical** Δt_σ (ratio 0.40 ± 0.01)
- Dominates at fine grids (grid refinement by 2× reduces Δt by factor 2.83)
- For water-air (σ ≈ 0.073 N/m): Δt_σ ≈ 5.5 × Δx^{3/2}

### 3. Cross-Derivative Viscous CFL (tightest at high viscosity ratio)

```
Δt_cross = C_cross · h² / (Δμ/ρ)
```

- C_cross ≈ 0.23 (verified constant ±10% across μ_l/μ_g = 1–1000)
- Only applies to explicit cross-derivative viscous terms; diagonal terms are CN-implicit
- For water-air (μ_l/μ_g ≈ 55): Δt_cross ≈ 0.23 · h²/(55·ν_g)
- **Becomes dominant at high viscosity ratios**

## Practical Regime Map

| Flow Regime | Dominant Constraint | Scaling |
|-------------|-------------------|---------|
| High-speed, coarse grid | Advective | O(h) |
| Surface-tension dominated, fine grid | Capillary | O(h^{3/2}) |
| High viscosity ratio | Cross-viscous | O(h²/Δμ) |
| Low Re, moderate σ | Capillary or cross-viscous | depends on ratio |

## Safety Margin Analysis

The production safety factor C_CFL = 0.45 provides:
- Advective: 0.45/0.91 = 49% of stability limit
- Capillary: 0.45 × 0.40 = 18% of theoretical limit (conservative)
- Cross-viscous: 0.45 vs C_cross = 0.23 — margin of 1.96�� (adequate)

All three constraints are simultaneously satisfied by the min() selection in §10 Step 0.

## Implementation Note

The CFL module (`src/twophase/time_integration/cfl.py`) must evaluate all three constraints and select the minimum. The capillary constraint requires surface tension coefficient σ and both phase densities; the cross-viscous constraint requires the viscosity jump Δμ.
