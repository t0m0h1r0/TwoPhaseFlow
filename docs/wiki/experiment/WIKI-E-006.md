---
ref_id: WIKI-E-006
title: "Young-Laplace Static Droplet (Exp 11-16)"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch11/exp11_16_young_laplace.py
    description: "Balanced-force CSF pipeline: static droplet pressure jump"
consumers:
  - domain: T
    usage: "Validates balanced-force CSF in [[WIKI-T-004]]"
  - domain: A
    usage: "Key validation result for §11 manuscript"
depends_on:
  - "[[WIKI-T-003]]"
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-008]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-08
---

## Exp 11-16: Young-Laplace Pressure Jump

Static circular droplet: R = 0.25, ρ_l/ρ_g = 1000, We = 1.
Exact solution: Δp = κ/We = 4.0.

### Setup
- CCD-based CSF pipeline: curvature κ → surface force → PPE → pressure field
- Interface smoothing: ε = 1.5h (Heaviside regularization)
- Field extension via CCD extrapolation across interface

### Results

| N | Δp measured | Relative error |
|---|-------------|----------------|
| 32 | ~3.97 | ~0.8% |
| 64 | ~3.99 | ~0.3% |
| 128 | ~3.992 | **~0.2%** |

### Significance

This is the canonical test for balanced-force methods. The result validates that:

1. **CCD curvature** provides accurate κ near the interface
2. **Balanced-force condition** is satisfied: same CCD operator for ∇p and σκ∇ψ
3. **CSF pipeline** correctly converts curvature → volumetric force → pressure jump
4. Spurious currents are controlled at ρ_l/ρ_g = 1000

**Key finding**: 0.2% relative error at N=128 for ρ_l/ρ_g = 1000 demonstrates that the CCD balanced-force CSF framework correctly recovers the Young-Laplace pressure jump.

## Limitation

This test uses a static droplet (u = 0). Dynamic validation with finite Weber number and interface deformation is covered by separate experiments (not in §11 scope — requires GFM for full two-phase PPE).
