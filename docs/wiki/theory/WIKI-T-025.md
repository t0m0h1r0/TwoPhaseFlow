---
ref_id: WIKI-T-025
title: "C/RC (CCD-Enhanced Rhie-Chow): O(h²) → O(h⁴) Bracket Correction"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: docs/memo/rc_ccd_high_order_correction.md
    git_hash: e62cd50
    description: "Richardson-type RC correction using CCD p''' to cancel h²/12 error → O(h⁴)"
  - path: docs/memo/rc_hermite_correction.md
    git_hash: e62cd50
    description: "Zero-cost O(h⁴) via CCD d2 (p''): Hermite, d2fd, d2cubic approaches compared"
  - path: docs/memo/crc_dccd_experiment_results.md
    git_hash: e62cd50
    description: "C/RC and C/RC-DCCD static droplet experiment results"
consumers:
  - domain: L
    usage: "RC correction module in ns_terms/"
  - domain: A
    usage: "§7 (Rhie-Chow high-order correction)"
depends_on:
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-017]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## Problem

Standard RC bracket: (∇p)_f − (∇p)_f̄ = O(h²). Even though CCD gives O(h⁶) cell-center derivatives, arithmetic averaging to face midpoints degrades to O(h²) because the h²/12·p''' term doesn't cancel.

## Approach 1: Richardson Correction (p''' Method)

Use CCD-computed p''' to cancel the leading error term:

(∇p)_f^corrected = (p_E−p_P)/h + h²/24 · (p'''_E + p'''_P) + O(h⁴)

RC bracket becomes O(Δt·h⁴). **Extra cost:** one additional CCD differentiate call per axis (compute d2 of p' to get p''').

## Approach 2: Hermite Correction (d2 Method, Zero Cost)

CCD simultaneously returns p'' = d2. Three variants explored:

1. **Hermite interpolation:** Theoretically best (O(h⁴) with coeff 1/480), but 1.5× face-gradient amplification destabilizes RC damping → **blows up in practice**
2. **d2fd:** Uses d2 in a finite-difference correction formula → **practical winner**, stable
3. **d2cubic:** Cubic Hermite interpolation → intermediate

## Experimental Results (Static Droplet)

### C/RC (CCD-enhanced RC)

Verified O(h⁴) convergence of RC bracket (vs O(h²) standard).

### C/RC-DCCD (Combined with DCCD Filter Correction)

Corrects DCCD filter's O(ε_d·h²) dissipation error using CCD d2 → O(ε_d·h⁴).

| Grid | Standard | C/RC-DCCD | Improvement |
|------|----------|-----------|-------------|
| N=32 | baseline | 5× better Laplace error | Significant |
| N=64 | baseline | ~same | CSF O(h²) dominates |

**Key finding:** C/RC improvement vanishes at higher resolution because CSF model error O(h²) rate-limits — the RC bracket correction is no longer the bottleneck.
