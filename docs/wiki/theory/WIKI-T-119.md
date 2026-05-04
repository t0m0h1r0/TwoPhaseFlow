---
ref_id: WIKI-T-119
title: "UCCD6 Hyperviscosity Exponent 7 Is the Minimal Order-Preserving Choice"
domain: theory
status: ACTIVE
superseded_by: null
tags: [uccd6, hyperviscosity, stability, order_preserving, ccd]
sources:
  - path: paper/sections/04d_uccd6.tex
    description: "UCCD6 k=4 hyperviscosity, exponent choice, and L2 stability"
depends_on:
  - "[[WIKI-T-062]]"
  - "[[WIKI-T-089]]"
  - "[[WIKI-T-117]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Minimal UCCD6 Hyperviscosity

## Knowledge Card

UCCD6 chooses an internal hyperviscosity proportional to

```text
h^7 * (-D2_CCD)^4
```

because this is the smallest construction that damps high wavenumbers while
remaining asymptotically below the sixth-order truncation error of the main CCD
advection operator.  A lower exponent competes with the leading low-wavenumber
accuracy; a higher exponent adds complexity and boundary sensitivity without
being necessary for the target damping role.

## Consequences

- UCCD6 dissipation is internal to the operator, not a post-filter.
- The exponent is tied to preserving the base operator's sixth-order accuracy.
- Explicit time integration faces severe high-wavenumber restrictions; CN or
  implicit treatment is structurally favored.
- Periodic-grid energy stability does not automatically prove bounded-domain
  stability under arbitrary closures.

## Paper-Derived Rule

Use UCCD6 hyperviscosity as the minimal order-preserving high-frequency damping
channel; do not lower the exponent just to gain stronger damping.
