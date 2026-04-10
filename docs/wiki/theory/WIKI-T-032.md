---
ref_id: WIKI-T-032
title: "Spatially Varying Epsilon: Theory for CSF on Non-Uniform Grids"
domain: T
status: PROPOSED
superseded_by: null
sources:
  - path: "docs/memo/spatially_varying_epsilon_theory.md"
    description: "Full theory memo with proofs and implementation architecture"
  - path: "docs/memo/grid_refinement_negative_result.md"
    description: "Root cause analysis of fixed-ε CSF mismatch"
consumers:
  - domain: E
    usage: "Implementation guide for eps_field in TwoPhaseNSSolver"
  - domain: A
    usage: "Paper §6 or §12 discussion of adaptive interface thickness"
depends_on:
  - "[[WIKI-T-009]]"
  - "[[WIKI-T-006]]"
  - "[[WIKI-T-020]]"
  - "[[WIKI-E-017]]"
  - "[[WIKI-E-018]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-11
---

# Spatially Varying Epsilon for CSF on Non-Uniform Grids

## Problem

Fixed ε = C_ε · h_uniform on interface-fitted grids (α>1) causes CSF force to spread over ε/h_local ≈ C_ε · α cells instead of the intended C_ε cells. This is the dominant source of Laplace pressure degradation observed in [[WIKI-E-018]] (68% vs 34% error at N=64).

## Solution: ε(x) = C_ε · h_local(x)

Replace scalar ε with a spatially varying field matching the local grid resolution.

### Three Key Properties

1. **Consistent cell count:** Interface transition always spans ~2C_ε local cells
2. **Automatic backward compatibility:** Reduces to scalar ε on uniform grids
3. **Smoothness:** Inherits smoothness from the grid density function ω(φ)

### What Changes

| Component | Effort | Notes |
|-----------|--------|-------|
| `heaviside()` | Trivial | NumPy broadcast (phi/eps works for array eps) |
| `delta()` | Trivial | `1/eps` broadcast |
| CurvatureCalculator | Minor | Pass eps_field to `invert_heaviside` (already array-capable) |
| TwoPhaseNSSolver | Minor | Add `_eps_field` property, recompute after grid rebuild |

### What Does NOT Change

- **Curvature formula** — ε-independent (curvature invariance theorem [[WIKI-T-020]])
- **PPE solver** — no ε dependency
- **Balanced-force condition** — operator consistency independent of ε
- **Advection** — CLS transport does not involve ε
- **Reinitializer** — use conservative scalar ε_min (pragmatic Option C)

### Reinitialization Note

The reinitialization PDE ∂ψ/∂τ + ∇·(n̂ψ(1−ψ)) = ε∇²ψ with spatially varying ε acquires an extra term ∇ε·∇ψ. Three options analyzed; Option C (scalar ε_min for reinit) is recommended because the reinit fixed point only needs to maintain a monotonic transition, and the exact profile width far from the interface is irrelevant for CSF.

### Expected Impact

- **Laplace pressure:** Error should converge O(h²) independent of α (fix the 68% degradation)
- **Parasitic currents:** Further reduction beyond [[WIKI-E-018]] results
- **Mass conservation:** No change (dominated by CLS advection)

### ε-Consistency Theorem

If ε(x) = C_ε · h_local(x) with smooth grid density:
1. H_{ε(x)} is smooth
2. CSF force integral ∫f_σ dx = σκ (preserved)
3. Balanced-force cancellation order unchanged
4. Laplace error O(h_local²) ≈ O(h²/α²) near interface

See full proof in `docs/memo/spatially_varying_epsilon_theory.md` §8.
