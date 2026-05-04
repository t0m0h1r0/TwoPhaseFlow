---
ref_id: WIKI-T-100
title: "Pressure-Jump Closure Solves Jump Absorption, Not Every Capillary Limit"
domain: theory
status: ACTIVE
superseded_by: null
tags: [pressure_jump, ppe, capillary, verification_gate, hfe, curvature]
sources:
  - path: paper/sections/09b_split_ppe.tex
    description: "Jump-corrected face-gradient scope and remaining validation gates"
  - path: paper/sections/09f_pressure_summary.tex
    description: "Pressure-jump closure conditions and non-guarantees"
depends_on:
  - "[[WIKI-T-083]]"
  - "[[WIKI-T-098]]"
  - "[[WIKI-T-099]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Pressure-Jump Closure Scope

## Knowledge Card

The pressure-jump closure primarily prevents the Young--Laplace jump from being
lost as a smooth pressure degree of freedom.  It also aligns PPE and velocity
correction through the same jump-corrected face gradient.

It does not, by itself, prove all capillary behavior.  Curvature caps, HFE
effective accuracy, capillary CFL, wall effects, and long-time geometric energy
stability remain separate validation gates.

## Consequences

- The closure is not a毛細管波-only patch; droplets, bubbles, flat interfaces,
  and waves use the same oriented jump law.
- Solving jump absorption does not solve curvature-quality limits.
- Sharing `H_f`, face coefficients, and divergence between PPE and correction is
  the closure guarantee.
- Capillary dynamics still require physical and long-time validation beyond PPE
  assembly.

## Paper-Derived Rule

Do not overclaim the pressure-jump PPE: it preserves interface stress information
inside projection; it does not certify every capillary regime.
