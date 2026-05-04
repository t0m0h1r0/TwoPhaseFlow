---
ref_id: WIKI-T-132
title: "Balanced-Force Mismatch Is a Positive Feedback Loop"
domain: theory
status: ACTIVE
superseded_by: null
tags: [balanced_force, spurious_currents, feedback_loop, pressure, curvature]
sources:
  - path: paper/sections/08_collocate.tex
    description: "Operator mismatch residual and parasitic-flow feedback chain"
depends_on:
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-105]]"
  - "[[WIKI-T-122]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Balanced-Force Feedback Loop

## Knowledge Card

Balanced-force mismatch is not a fixed one-step forcing error.  In the paper's
static-droplet explanation, an operator mismatch leaves an artificial body force
after pressure and surface tension should cancel.  That force drives a parasitic
velocity, which advects the CLS interface, which changes curvature, which then
increases the next surface-tension mismatch.

The failure is therefore a feedback loop:

```text
operator mismatch -> parasitic velocity -> interface deformation
-> curvature error -> larger mismatch
```

## Consequences

- Small one-step residuals can become explosive when coupled to interface
  transport.
- Curvature fixes alone do not cure a pressure/surface-force operator mismatch.
- Static-droplet tests probe a dynamical feedback, not only an equilibrium
  algebra identity.
- Checkerboard-prone pressure modes can amplify residuals that the PPE residual
  norm does not make obvious.

## Paper-Derived Rule

Treat balanced-force violations as coupled positive-feedback defects; fix the
shared operator contract before tuning curvature or timestep knobs.
