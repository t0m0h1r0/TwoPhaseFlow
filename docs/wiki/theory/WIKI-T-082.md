---
ref_id: WIKI-T-082
title: "Defect Correction Scope: High-Order Residual, Not Interface-Band Cure"
domain: theory
status: ACTIVE
superseded_by: null
tags: [defect_correction, ppe, ccd, interface_band, split_ppe, convergence]
sources:
  - path: paper/sections/09d_defect_correction.tex
    description: "Defect-correction accuracy scope and PPE-configuration convergence table"
depends_on:
  - "[[WIKI-T-005]]"
  - "[[WIKI-T-015]]"
  - "[[WIKI-T-079]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Defect Correction Scope

## Knowledge Card

Defect correction preserves the high-order accuracy of the high-order operator
only when the high-order residual is actually driven down.  The low-order
operator is an accelerator; the residual evaluated by the high-order operator
defines the target accuracy.

Therefore a fixed iteration count, such as `k=3`, is not a universal accuracy
contract.  It is an observed practical upper target for phase-separated PPE
contexts, not a cure for every pressure equation.

## Consequences

- `k=3` must not be cited as proof of high-order accuracy by itself.
- Lumped variable-density PPE can still plateau through interface-band error.
- Smoothed-Heaviside products can limit convergence even under DC.
- Phase-separated PPE is the route that gives DC a compatible smooth residual.

## Paper-Derived Rule

Use DC to converge a high-order residual in a compatible smooth problem; do not
use it as a bandage for an ill-posed one-fluid interface-band operator.
