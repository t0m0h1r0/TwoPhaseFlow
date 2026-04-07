---
ref_id: WIKI-T-004
title: "Balanced-Force Condition: Operator Consistency Principle"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/08_collocate.tex
    git_hash: 7328bf1
    description: "Balanced-Force theory, operator mismatch analysis, C/RC correction"
consumers:
  - domain: L
    usage: "pressure/velocity_corrector.py and ns_terms/surface_tension.py must use same CCD operator"
  - domain: E
    usage: "Stationary droplet benchmark validates BF via parasitic current measurement"
  - domain: A
    usage: "Core design argument connecting CCD to physical accuracy"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-003]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## The Problem: Parasitic Currents

At a stationary interface, the momentum equation reduces to:

grad(p) = sigma * kappa * grad(psi)

If the discrete pressure gradient operator differs from the discrete surface tension gradient operator, a residual O(h^2) force appears as non-physical **parasitic currents** that can grow and destabilize the simulation.

## Balanced-Force Principle

**Use the same CCD operator** for both:
1. Pressure gradient: grad_CCD(p) in the corrector step
2. Surface tension gradient: sigma * kappa * grad_CCD(psi) in the predictor step

When both use CCD, the discrete equilibrium is satisfied to O(h^6) precision, and parasitic currents scale as O(10^-5) at N=64 instead of O(10^-2) with mixed FD/CCD operators.

## Quantitative Impact

| Method | Operator pair | Parasitic current order (N=64) |
|--------|--------------|-------------------------------|
| FVM + CSF | FVM grad / FVM grad | O(10^-2) |
| Mixed FD-PPE + CCD-grad | FD / CCD | O(10^-2) — mismatch |
| CCD-PPE + CCD-grad | CCD / CCD | O(10^-5) |

**Note**: All methods share the O(h^2) CSF model error floor. CCD Balanced-Force eliminates the additional discretization mismatch error, leaving only the CSF model error.

## C/RC (CCD-enhanced Rhie-Chow)

Standard Rhie-Chow face interpolation has O(h^2) bracket error. C/RC improves this to O(h^4) by leveraging CCD's simultaneous f' availability. C/RC-DCCD further corrects the DCCD dissipation error from O(eps_d h^2) to O(eps_d h^4).

**Status**: C/RC-DCCD is formulated (eq:crc_dccd in S8) but its activation in the current 7-step algorithm (S10) is not explicitly confirmed. The standard algorithm uses eq:dccd_ppe_rhs without C/RC correction.

## Design Implication

The Balanced-Force requirement is the primary reason CCD is used for PPE solving (not just differentiation). Using FD for PPE + CCD for gradient would create the operator mismatch. The current DC solver (k=1) gives effective O(h^2) for PPE but maintains BF because the CCD gradient operator is applied to the DC-corrected pressure.
