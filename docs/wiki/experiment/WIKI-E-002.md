---
ref_id: WIKI-E-002
title: "Curvature & Hermite Field Extension (Exp 11-3, 11-7)"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch11/exp11_3_curvature_3path.py
    description: "Curvature κ = −div(∇φ/|∇φ|) convergence: CCD vs CD2"
  - path: experiment/ch11/exp11_7_hfe_convergence.py
    description: "Hermite field extension convergence: 1D and 2D"
consumers:
  - domain: T
    usage: "Validates curvature computation in [[WIKI-T-008]]"
  - domain: A
    usage: "Curvature convergence tables for §11"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-008]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-08
---

## Exp 11-3: Curvature Convergence

κ = −∇·(∇φ/|∇φ|) computed near interface (N = 16–256):

| Case | CCD | CD2 |
|------|-----|-----|
| (a) Circle R=0.25, κ_exact=4 | O(h^{4–5}) L∞ | O(h^2) L∞ |
| (b) Sinusoidal y=0.5+0.05sin(2πx) | O(h^{4–5}) L∞ | O(h^2) L∞ |

**Key finding**: CCD curvature achieves 2–3 orders higher accuracy than standard CD2 at the same grid resolution. The gain comes from simultaneous f'/f'' availability — no separate finite-difference approximation for second derivatives.

## Exp 11-7: Hermite Field Extension (HFE)

Closest-point extension of field q from interface into band:

| Case | Method | Order |
|------|--------|-------|
| (a) 1D φ=x−0.5 | Upwind extension | O(h^1) |
| (a) 1D φ=x−0.5 | Hermite extension | O(h^{6+}) |
| (b) 2D circle R=0.25 | Tensor-product HFE | O(h^3) |

**Key finding**: 1D Hermite extension achieves CCD-level O(h^6+) accuracy. 2D tensor-product HFE degrades to O(h^3) due to closest-point coordinate curvature effects — still significantly better than upwind O(h^1).

## Cross-cutting Insights

- CCD-based curvature provides the high accuracy needed for balanced-force CSF (see [[WIKI-T-004]])
- HFE leverages CCD's simultaneous (f, f', f'') to extrapolate interface quantities
- 2D HFE order loss (h^6 → h^3) is a known geometric effect, not a discretization defect
