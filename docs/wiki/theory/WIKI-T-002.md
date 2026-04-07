---
ref_id: WIKI-T-002
title: "Dissipative CCD Filter: Theory and Adaptive Control"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/04d_dissipative_ccd.tex
    git_hash: 7328bf1
    description: "DCCD filter definition, transfer function, switch function, conservation analysis"
  - path: paper/sections/10b_implementation_details.tex
    git_hash: 7328bf1
    description: "eps_d spectral design, adaptive control algorithm"
consumers:
  - domain: L
    usage: "Multiple modules apply DCCD with different parameter regimes"
  - domain: A
    usage: "DCCD appears in S4, S7, S8, S10 with cross-cutting role"
  - domain: E
    usage: "Filter strength affects convergence rates and parasitic currents"
depends_on:
  - "[[WIKI-T-001]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## Problem Statement

Standard CCD has zero numerical dissipation (purely imaginary modified wavenumber). In nonlinear two-phase flow, this causes aliasing instability and grid-scale noise accumulation. DCCD adds controlled dissipation using the same 3-point stencil.

## Filter Definition

The 3-point spectral filter:
- f'_filtered = f'_CCD - eps_d * h * f''_CCD
- f''_filtered = f''_CCD - eps_d * (2/h) * (f_{i-1} - 2f_i + f_{i+1})  [approximate]

Transfer function: H(xi; eps_d) = 1 - 4*eps_d*sin^2(xi/2), where xi = kh (normalized wavenumber).

Key properties:
- H(0) = 1 (DC preserved)
- H(pi) = 1 - 4*eps_d (Nyquist damping)
- Stability requires eps_d <= 1/4 (H >= 0)

## Three Distinct Usage Modes

See [[WIKI-X-001]] for the complete cross-algorithm map.

| Mode | eps_d | S(psi) control | Context |
|------|-------|----------------|---------|
| Adaptive | eps_{d,max} * S(psi_i) | YES | Velocity/pressure fields — zero at interface, max in bulk |
| Uniform | 0.05 | NO | CLS advection/reinitialization — interface needs dissipation |
| Checkerboard | 1/4 | NO | PPE RHS divergence — maximum permitted strength |

## Switch Function S(psi)

S(psi) = (2*psi - 1)^2

- S(0) = S(1) = 1 (pure phase: full dissipation)
- S(0.5) = 0 (interface center: zero dissipation)
- Equivalently: S(phi) = tanh^2(phi / 2*epsilon) in level-set coordinates

**Why NOT used for CLS advection**: The CLS profile itself IS the interface; S(psi)=0 at psi=0.5 would disable the filter precisely where advection instability is worst.

## Spectral Design: eps_{d,max} = 0.05

Dual constraint optimization:
- **Accuracy**: wavelength >= 6h must retain >= 95% amplitude -> eps_d <= 0.05
- **Damping**: Nyquist (2h) must lose >= 20% amplitude -> eps_d >= 0.05

Both constraints meet at eps_{d,max} = 0.05. At this value:
- DC: 100%, 6h: 95%, 3h: 85%, Nyquist: 80%

Aggressive options (eps_d = 0.10-0.20) available for high-Re/high-density-ratio with 10-20% accuracy loss at 6h wavelength.

## Conservation

DCCD is a derivative-field filter (non-conservative form), consistent with the advective-form NS discretization used in this monograph. A flux-form variant exists for future FVM migration but is not currently implemented.
