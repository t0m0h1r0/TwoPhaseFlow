---
ref_id: WIKI-E-004
title: "Rhie-Chow & PPE Solver Verification (Exp 11-5, 11-9, 11-10, 11-11, 11-12, 11-13)"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch11/exp11_5_rc_bracket.py
    description: "Rhie-Chow bracket accuracy: standard vs corrected"
  - path: experiment/ch11/exp11_9_dc_k_accuracy.py
    description: "Defect correction iteration count vs accuracy"
  - path: experiment/ch11/exp11_10_dc_vs_fd.py
    description: "DC k=3 vs FD direct cost-accuracy comparison"
  - path: experiment/ch11/exp11_11_ppe_neumann.py
    description: "PPE Neumann BC + gauge fixing"
  - path: experiment/ch11/exp11_12_varrho_ppe.py
    description: "Variable-density PPE convergence"
  - path: experiment/ch11/exp11_13_dc_omega_map.py
    description: "DC ω-relaxation convergence map"
consumers:
  - domain: T
    usage: "Validates DC-PPE solver in [[WIKI-T-005]]"
  - domain: L
    usage: "Informs solver parameter choices (k=3, ω≤0.833)"
depends_on:
  - "[[WIKI-T-003]]"
  - "[[WIKI-T-005]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-08
---

## Exp 11-5: Rhie-Chow Bracket

Face gradient interpolation for p = cos(2πx)cos(2πy), periodic BC (N = 16–128):

| Method | Order |
|--------|-------|
| Standard bracket | O(h^2) |
| Corrected (C/RC) bracket with h/24 term | O(h^4) |

**Key finding**: The h/24 correction term upgrades Rhie-Chow face gradient accuracy by 2 orders. This is critical for balanced-force consistency at high accuracy.

## Exp 11-9: DC Iteration Count vs Accuracy

2D Poisson Δp = f, Dirichlet BC, p* = sin(πx)sin(πy). L_H = CCD O(h^6), L_L = FD O(h^2):

| DC iterations k | Convergence order |
|-----------------|-------------------|
| 1 | O(h^2) — FD level |
| 2 | O(h^4) — intermediate |
| 3 | **O(h^7)** — super-convergence (Dirichlet) |
| 5 | O(h^7) — saturated |
| 10 | O(h^7) — saturated |

**Key finding**: k=3 is the optimal iteration count — achieves super-convergence beyond O(h^6) for Dirichlet. Additional iterations provide no benefit. This justifies the DC k=3 design choice in the solver.

## Exp 11-10: DC k=3 vs FD Direct

Cost-accuracy tradeoff at N = 8–128:

| N | FD error | DC k=3 error | Accuracy ratio | Cost ratio |
|---|----------|--------------|----------------|------------|
| 128 | ~1e-4 | ~1e-11 | **4.9e7×** better | 3.4× slower |

**Key finding**: DC k=3 trades 3.4× compute cost for nearly 8 orders of magnitude accuracy improvement. The CCD residual computation dominates cost; FD LU solve is reused across iterations.

## Exp 11-11: PPE Neumann BC

All-Neumann BC with gauge pinning p_{0,0} = p*(0,0), DC k=3 (N = 8–128):

| Result |
|--------|
| O(h^5) convergence |

**Key finding**: Neumann BC reduces convergence from O(h^7) (Dirichlet) to O(h^5). The CCD boundary scheme O(h^5) is the bottleneck — consistent with Exp 11-1(b) wall BC result.

## Exp 11-12: Variable-Density PPE

∇·(1/ρ ∇p) = f with CCD product rule:

### (a) Smooth density ρ = 1 + A·sin(πx)cos(πy)

| Amplitude A | Order |
|-------------|-------|
| 0 (constant) | O(h^{6–7}) |
| 0.8 | O(h^{6–7}) |
| 0.98 | O(h^{6–7}) |
| 0.998 | O(h^{6–7}) |

### (b) Interface-type density (smoothed Heaviside)

| ρ_l/ρ_g | Result |
|----------|--------|
| 10 | **Diverges** |
| 100 | **Diverges** |
| 1000 | **Diverges** |

**Key finding**: Smooth density variations preserve O(h^6–7) regardless of amplitude. However, sharp density jumps (even smoothed Heaviside) cause DC divergence — the CCD product-rule stencil cannot handle the near-discontinuous 1/ρ coefficient. This is a known limitation motivating GFM or IIM approaches.

## Exp 11-13: DC ω-Relaxation Map

Variable-density Neumann PPE with under-relaxation ω (N = 32, 64):

| ω | ρ_l/ρ_g = 1 | ρ_l/ρ_g = 10 | ρ_l/ρ_g = 1000 |
|---|-------------|-------------|---------------|
| 0.1 | ~20 iter | ~40 iter | Stagnated |
| 0.5 | ~8 iter | ~15 iter | Stagnated |
| 0.83 | ~5 iter | ~10 iter | Diverged |

**Key finding**: ω = 0.833 is the theoretical optimum for low density ratios. At high ratios (≥100), convergence fails regardless of ω — consistent with Exp 11-12(b). The spectral radius exceeds unity when ρ_l/ρ_g is large with Neumann BC.

## Cross-cutting Insights

- **DC k=3 is the design point**: 3 iterations unlock super-convergence; more iterations add cost without benefit
- **Neumann BC is the accuracy bottleneck**: O(h^5) boundary closure limits global convergence
- **High density ratio is the solver's Achilles heel**: smooth density OK, sharp jumps break DC convergence — GFM needed for two-phase PPE
- **Rhie-Chow correction is essential**: without h/24 term, face gradient drops to O(h^2), breaking balanced-force consistency
