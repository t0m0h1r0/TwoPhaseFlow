---
ref_id: WIKI-T-102
title: "Viscous Helmholtz DC Shares Coefficients, Boundaries, and Interface Bands"
domain: theory
status: ACTIVE
superseded_by: null
tags: [viscosity, bdf2, defect_correction, helmholtz, cross_terms, interface_band]
sources:
  - path: paper/sections/07_time_integration.tex
    description: "Implicit-BDF2 viscous Helmholtz and defect-correction contract"
  - path: paper/sections/11_full_algorithm.tex
    description: "Predictor-stage viscous Helmholtz DC in the full algorithm"
depends_on:
  - "[[WIKI-T-082]]"
  - "[[WIKI-T-091]]"
  - "[[WIKI-T-092]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Viscous Helmholtz DC Sharing Contract

## Knowledge Card

Implicit-BDF2 removes the pure viscous CFL by solving a viscous Helmholtz problem,
but defect correction is still constrained.  The low-order correction operator
may simplify the solve, yet it must share the same `mu`, `rho`, boundary phase,
and interface-band classification as the high-order full-stress residual.

The cross-viscous terms belong in the high-order residual at the same time level;
they are not explicitly lagged side terms.

## Consequences

- Dropping `A_L` to a constant-coefficient Poisson/Helmholtz surrogate can change
  the fixed-point problem.
- Cross terms can be separated in the correction solve only if the high-order
  residual restores them.
- Viscous DC accuracy is judged by the full-stress `A_H` residual.
- A-stability removes the pure viscous CFL, not every possible explicit residual
  restriction.

## Paper-Derived Rule

Use low order to make viscous correction cheap, not to change the material,
boundary, or interface physics of the high-order residual.
