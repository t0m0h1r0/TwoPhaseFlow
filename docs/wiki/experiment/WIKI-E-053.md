---
ref_id: WIKI-E-053
title: "V7 RCA Localizes the Time-Order Limit to the Capillary Jump Band"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter13, v7, rca, time_order, capillary_jump, interface_band]
sources:
  - path: paper/sections/13d_density_ratio.tex
    description: "V7 root-cause analysis of coupled-stack time-order limitation"
depends_on:
  - "[[WIKI-T-103]]"
  - "[[WIKI-T-138]]"
  - "[[WIKI-E-041]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# V7 Capillary-Band Limiter

## Knowledge Card

V7's time-order limitation is localized by RCA to the capillary
pressure-jump/projection interface band.  The final local slope is therefore
read as a Type-D coupled-stack limitation, not as generic BDF2 failure.

The rejected explanations matter:

```text
not reinit cadence
not Lie splitting alone
not density or viscosity contrast alone
```

## Consequences

- The observed sub-second-order slope should be tied to the capillary
  jump/projection closure band.
- Fixes should target face jump consistency and interface-band projection, not
  merely the global time integrator.
- V7 is evidence about the hardest coupled capillary stack, not about every
  time primitive in isolation.
- The RCA preserves earlier U8 second-order primitive results by separating
  primitive accuracy from coupled-stack limitation.

## Paper-Derived Rule

Use V7 as a localized capillary-band RCA result: the limiter lives at the
pressure-jump/projection interface, not in BDF2 alone.
