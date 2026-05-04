---
ref_id: WIKI-T-127
title: "Viscous DC Low-Order Operator Must Share mu, rho, Boundaries, and Bands"
domain: theory
status: ACTIVE
superseded_by: null
tags: [viscous, helmholtz, defect_correction, material_properties, interface_band, bdf2]
sources:
  - path: paper/sections/07_time_integration.tex
    description: "Viscous Helmholtz defect correction and low-order operator constraints"
depends_on:
  - "[[WIKI-T-091]]"
  - "[[WIKI-T-102]]"
  - "[[WIKI-T-126]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Viscous DC Shared Coefficients

## Knowledge Card

For the implicit-BDF2 viscous Helmholtz solve, the low-order correction operator
may simplify the stress coupling, but it must not drop the physics that makes
the high-order operator hard:

```text
same mu
same rho
same boundary phase
same interface-band closures
```

A constant-coefficient Poisson-like correction is forbidden for large
viscosity/density jumps because it can be spectrally too far from the
high-order Helmholtz fixed point.

## Consequences

- The low-order viscous solver is a preconditioner, not a different PDE.
- Cross terms can live in the high-order residual, but coefficient/boundary
  identity cannot be discarded.
- Large `tau` and sharp jumps demand closer `A_L`/`A_H` alignment.
- Viscous CFL removal does not remove the need for robust Helmholtz correction.

## Paper-Derived Rule

In viscous DC, simplify coupling only after preserving the same material,
boundary, and interface-band structure as the high-order stress operator.
