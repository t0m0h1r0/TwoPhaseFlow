---
id: WIKI-E-015
title: "§13 Benchmark Suite: 8 Physical Validation Experiments with Reference Solutions"
status: ACTIVE
created: 2026-04-10
updated: 2026-04-10
depends_on: [WIKI-E-008, WIKI-L-014, WIKI-X-007]
---

# §13 Benchmark Suite

## Overview

8 experiments progressing from single-body static → single-body dynamic → multi-body
interaction → analytical deformation.  All run via `experiment/ch13/run.py` with YAML configs
in `experiment/ch13/config/`.

| ID | Name | Type | Bodies | Reference |
|----|------|------|:------:|-----------|
| §13.1 | Static droplet parasitic current | grid sweep | 1 | Popinet 2009 |
| §13.2 | Capillary wave decay | single run | 1 | Prosperetti 1981 |
| §13.3 | Single rising bubble | single run | 1 | Hysing et al. 2009 |
| §13.4 | RT instability σ>0 | σ sweep | — | Tryggvason 1988 |
| §13.5 | Two-droplet collision | We sweep | 2 | Nobari & Tryggvason 1996 |
| §13.6 | Two-bubble DKT | single run | 2 | Esmaeeli & Tryggvason 1998 |
| §13.7 | Bubble swarm (N=9) | single run | 9 | Tryggvason et al. 2001 |
| §13.8 | Taylor deformation | Ca×λ sweep | 1 | Taylor 1932 |

## §13.1: Static Droplet — Parasitic Current Convergence

**Goal:** Measure spurious velocity ‖u_para‖∞ and Laplace Δp error vs grid spacing.

- Domain [0,1]², wall BC, R=0.25, σ=1.0, no gravity
- ρ_l/ρ_g = 100, sweep N ∈ {32, 64, 128, 256}, 500 steps each
- **Criterion:** O(h²) convergence in both ‖u_para‖∞ and |Δp − σ/R|/(σ/R)
- **Key insight:** Balanced-force CSF achieves O(h²) for parasitic currents;
  GFM-based approaches (§8e) could improve to O(h⁴) but are not yet in the monolithic pipeline

## §13.2: Capillary Wave Decay

**Goal:** Verify surface-tension-driven oscillation frequency and viscous decay.

- Perturbed circle r(θ) = R₀(1 + ε cos(2θ)), ε = 0.05, R₀ = 0.25
- ρ_l = 10, ρ_g = 1, μ = 0.05, σ = 1.0
- **Analytical (Prosperetti 1981):**
  - ω₀² = l(l−1)(l+2)σ / [(ρ_l+ρ_g) R₀³], l = 2 → ω₀ ≈ 6.82
  - β = (2l+1)(2l−1)μ / [(ρ_l+ρ_g) R₀²] ≈ 0.048 (leading-order viscous decay)
- **Metric:** D(t) = (L−B)/(L+B) from 2nd moments; compare period T and decay β

**New primitive required:** `PerturbedCircle` shape (added to shapes.py)

## §13.3: Single Rising Bubble (Hysing Case 1, Modified)

**Goal:** Validate buoyancy-driven bubble dynamics.

- Hysing Case 1 non-dimensional: Re = 35, Eo = 10
- ρ_l/ρ_g = 10 (modified; full Case 1 uses 1000 → needs split PPE)
- **Derived physics** (g = 1, d = 0.5):
  - σ = g ρ_l d² / Eo = 0.2250
  - μ = ρ_l √(gd) d / Re = 0.1010
- Domain [0,1]×[0,2], 64×128, T = 3.0
- **Metrics:** centroid y_c(t), rise velocity v_c(t), |ΔV|/V₀ < 0.5%

## §13.4: RT Instability with Surface Tension

**Goal:** Show σ-stabilization of Rayleigh-Taylor.

- ρ_l = 3, ρ_g = 1, μ = 0.01, g = 1; sinusoidal perturbation y = 2 + 0.05 sin(2πx)
- σ sweep: {0.0, 0.02, 0.05}
- **Theory:** ω² = gk(ρ_l−ρ_g)/(ρ_l+ρ_g) − σk³/(ρ_l+ρ_g) with k = 2π
  - k_c = √(g(ρ_l−ρ_g)/σ): at σ = 0.05, k_c ≈ 6.32 ≈ k → marginal stability
- **Metric:** Interface amplitude η(t); at σ = 0.05 growth is strongly suppressed

## §13.5: Two-Droplet Head-On Collision

**Goal:** Test topology change (coalescence) and mass conservation under high density ratio.

- ρ_l/ρ_g = 1000, μ_l/μ_g = 100, two R = 0.25 droplets approaching at v₀ = 0.1
- We = ρ_l v₀² d / σ; sweep We ∈ {0.5, 2.0, 5.0}
  - σ = 1000 × 0.01 × 0.5 / We → {10.0, 2.5, 1.0}
- **Criterion:** |ΔV|/V₀ < 0.1% through coalescence event

**New primitives required:** `DropletPairApproach` velocity field, `union` IC type

## §13.6: Two-Bubble DKT

**Goal:** Qualitative drafting–kissing–tumbling dynamics.

- Same physics as §13.3 but ρ_l/ρ_g = 1000; two R = 0.25 bubbles at (1,0.5) and (1,1.1)
- Domain [0,2]×[0,8], 64×256
- **Observable:** y-separation Δy(t) decreases (drafting), near-zero (kissing),
  then horizontal separation (tumbling)
- **Criterion:** trailing bubble peak velocity ≥ 1.2× single-bubble terminal velocity

## §13.7: 9-Bubble Swarm (Periodic Domain)

**Goal:** Multi-body collective rise; test periodic PPE + long-time stability.

- 3×3 bubble array, R = 0.25 each, void fraction α ≈ 0.196
- ρ_l/ρ_g = 100, Re = 50, Eo = 4; doubly-periodic [0,3]², 128²
- T = 20 (long-time run)
- **Criterion:** U_swarm/U_single = f(α) within 20% of Tryggvason DNS

## §13.8: Taylor Droplet Deformation

**Goal:** Cleanest analytical validation of shape deformation.

- Neutrally buoyant (ρ_l = ρ_g = 1), Couette shear u = γ̇(y − Ly/2), γ̇ = 2.0
- Ca = μ_g γ̇ R / σ; sweep Ca ∈ {0.1, 0.2, 0.3, 0.4} × λ ∈ {1, 5}
  - σ = 0.1 × 2.0 × 0.25 / Ca = 0.05 / Ca
- **Analytical (Taylor 1932):** D_theory = (19λ+16)/(16λ+16) × Ca
- **Criterion:** |D_sim − D_th|/D_th < 10% for Ca ≤ 0.3

**New primitives required:** `CouetteShear` velocity field, `couette` BC hook

## §12 → §13 Progression

| Aspect | §12 (consistency) | §13 (validation) |
|--------|--------------------|-------------------|
| Density ratio | 1–100 | 10–1000 |
| Surface tension | off or low | physically relevant σ |
| Gravity | off or weak | buoyancy-driven flow |
| Multi-body | never | §13.5–13.7 |
| Reference | manufactured solutions | published benchmarks |
| PPE | monolithic | monolithic (§13.1–4), split (§13.5–7) |
