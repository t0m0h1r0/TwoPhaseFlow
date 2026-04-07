---
ref_id: WIKI-E-007
title: "Static Droplet Benchmark: Implementation Protocol, C/RC Results, and Negative Results"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: "docs/memo/実験_静止液滴シミュレーションの確立.md"
    git_hash: e62cd50
    description: "3-phase validation protocol for static droplet parasitic current suppression"
  - path: docs/memo/grid_refinement_negative_result.md
    git_hash: e62cd50
    description: "Negative result: non-uniform grid refinement worsens parasitic currents ~400x"
  - path: docs/memo/crc_dccd_experiment_results.md
    git_hash: e62cd50
    description: "C/RC and C/RC-DCCD experimental results on static droplet"
consumers:
  - domain: L
    usage: "Static droplet benchmark test parameters and expected results"
  - domain: A
    usage: "§11 verification chapter, §12 benchmark chapter"
depends_on:
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-025]]"
  - "[[WIKI-E-006]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## 3-Phase Validation Protocol

### Phase I: Curvature Accuracy

Target: O(h⁶) convergence of κ from CCD. Verify on known analytic circle (R=0.25).

### Phase II: Inviscid Balanced-Force

Static droplet, zero viscosity. Expect machine-epsilon spurious velocity if balanced-force holds exactly. Tests operator consistency between ∇p (CCD) and σκ∇ψ (CCD).

### Phase III: Laplace-Number Sensitivity

Vary La = σρR/μ². Track Ca (capillary number of parasitic currents) vs time. Verify convergence to equilibrium.

### Key Parameters

- Smooth Heaviside for interface (not sharp)
- PPE tolerance: ~1e-10 (strict)
- Capillary CFL: Δt < √(ρh³/(2πσ))

## Negative Result: Non-Uniform Grid Refinement

Grid clustering (alpha_grid = 1, 2, 4) tested on static droplet.

| alpha | Laplace error | Parasitic currents | DC-PPE solver |
|-------|--------------|-------------------|---------------|
| 1 (uniform) | baseline | baseline | converges |
| 2 | improved | ~10× worse | converges |
| 4 | 0.2% (best) | **~400× worse** | **diverges** |

**Root cause:** h_min shrinks with alpha → CFL forces many more timesteps → error accumulates. DC solver diverges because CCD and FD operators have incompatible high-frequency spectral response at non-uniform spacing.

**Conclusion:** Non-uniform grid refinement is counterproductive for parasitic current suppression. Uniform grids recommended.

## C/RC Experimental Results

### C/RC (CCD-Enhanced Rhie-Chow)

Uses CCD d2 to correct p''' mismatch. Verified O(h⁴) convergence of RC bracket (vs O(h²) standard).

### C/RC-DCCD

Corrects DCCD filter dissipation error using CCD d2: O(ε_d·h²) → O(ε_d·h⁴).

- N=32: **5× improvement** in Laplace pressure error
- N=64: improvement vanishes — **CSF O(h²) error dominates** over filter dissipation

**Key takeaway:** RC bracket correction matters at coarse grids but becomes irrelevant at fine grids where CSF model error rate-limits.
