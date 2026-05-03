---
ref_id: WIKI-T-093
title: "rho/mu Are Post-CLS Algebraic Fields, Not High-Order Interpolants"
domain: theory
status: ACTIVE
superseded_by: null
tags: [density, viscosity, material_property, cls, ordering, interpolation]
sources:
  - path: paper/sections/06d_viscous_3layer.tex
    description: "rho/mu algebraic update, face/corner mu averaging, and failure modes"
depends_on:
  - "[[WIKI-T-078]]"
  - "[[WIKI-T-085]]"
  - "[[WIKI-T-091]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# rho/mu Are Post-CLS Algebraic Fields

## Knowledge Card

Density and viscosity are not independently high-order reconstructed fields in
the paper's standard path.  They are algebraic consequences of the finalized
post-Stage-F `psi^{n+1}`:

```text
rho = rho_g + (rho_l - rho_g) psi
mu  = mu_g  + (mu_l  - mu_g)  psi
```

This ordering guarantees bounds when `psi in [0,1]` and prevents property Gibbs
oscillations from entering the momentum predictor or PPE.

## Consequences

- Update `rho` and `mu` only after CLS value limiting and final mass closure.
- Do not apply CCD/UCCD6 directly to step-like material properties.
- Face/corner `mu` is a low-order auxiliary quantity, not the default colocated
  stress path.
- Arithmetic averaging is the baseline for CLS diffuse-interface viscosity.
- Harmonic averaging is a sensitivity/sharp-interface comparison, not the
  default for high-viscosity-ratio diffuse interfaces.

## Paper-Derived Rule

Material properties inherit their admissibility from finalized `psi`; they do not
earn independent high-order reconstruction rights.
