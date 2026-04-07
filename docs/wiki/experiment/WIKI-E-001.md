---
ref_id: WIKI-E-001
title: "CCD/DCCD Spatial Accuracy Verification (Exp 11-1, 11-2, 11-4)"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch11/exp11_1_ccd_convergence.py
    description: "CCD convergence: periodic/wall BC, uniform/non-uniform grid"
  - path: experiment/ch11/exp11_2_dccd_filter.py
    description: "DCCD filter transfer function and checkerboard suppression"
  - path: experiment/ch11/exp11_4_gcl_nonuniform.py
    description: "GCL compliance and non-uniform grid accuracy"
consumers:
  - domain: T
    usage: "Validates O(h^6) claim in [[WIKI-T-001]]"
  - domain: A
    usage: "Convergence tables for §11 manuscript"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-002]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-08
---

## Exp 11-1: CCD Convergence

Three sub-cases validate CCD differentiation accuracy (N = 16–256):

| Case | BC | Grid | Target | Result |
|------|----|------|--------|--------|
| (a) sin(2πx) | Periodic | Uniform | O(h^6) | **PASS** — O(h^6) for f', f'' |
| (b) exp(x) | Wall (Dirichlet) | Uniform | O(h^5) | **PASS** — boundary closure limits to O(h^5) |
| (c) sin(2πx) | Periodic | Non-uniform α=2 | O(h^6) | **PASS** — coordinate transform preserves order |

**Key finding**: N=256 reaches machine precision (~1e-15) for periodic case.

## Exp 11-2: DCCD Filter Design

Transfer function H(ξ) at varying dissipation strengths ε_d:

| ε_d | H(π) (Nyquist) | Behavior |
|-----|-----------------|----------|
| 0.00 | 1.0 | No filtering (pure CCD) |
| 0.05 | ~0.8 | Mild dissipation |
| 0.25 | **0.0** | Complete Nyquist suppression |
| 0.50 | −0.5 | Over-dissipation (not recommended) |

**Key finding**: ε_d = 0.25 is the design point — zeroes H(π) for exact checkerboard removal. RMS of (−1)^{i+j} mode reduced to machine zero at N = 32, 64, 128.

## Exp 11-4: GCL on Non-uniform Grids

| Test | α | Result |
|------|---|--------|
| Convergence f=sin(πx) | 1.0 (uniform) | O(h^6) |
| Convergence f=sin(πx) | 2.0 (non-uniform) | O(h^6) |
| GCL f=1 (constant) | 2.0 | |df/dx|∞ ≤ 2.2e-13 ≈ 1e3·ε_mach — **PASS** |

**Key finding**: Non-uniform coordinate transform preserves O(h^6) and satisfies GCL to machine precision.

## Cross-cutting Insights

- CCD achieves design accuracy O(h^6) in all tested configurations
- Boundary closure (wall BC) is the accuracy bottleneck: O(h^5)
- DCCD filter at ε_d = 0.25 provides exact checkerboard suppression without degrading smooth-mode accuracy
- Non-uniform grids maintain full accuracy when GCL is satisfied
