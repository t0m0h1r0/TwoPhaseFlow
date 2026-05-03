---
ref_id: WIKI-T-105
title: "Failure Modes Are Coupled Symptoms, Not Module Labels"
domain: theory
status: ACTIVE
superseded_by: null
tags: [failure_modes, spurious_currents, mass_loss, checkerboard, interface_tracking, diagnosis]
sources:
  - path: paper/sections/01_introduction.tex
    description: "Four interface-driven difficulties and their mapped failure examples"
depends_on:
  - "[[WIKI-P-003]]"
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-078]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Coupled Failure Symptoms

## Knowledge Card

The paper does not treat spurious currents, mass loss, checkerboard pressure,
and interface smearing as four independent software bugs.  It maps each visible
failure to one or more interface-driven numerical difficulties:

```text
spurious currents = curvature error + pressure/surface-force mismatch
mass loss         = non-conservative interface transport/reinitialization drift
checkerboard      = pressure-velocity decoupling on collocated grids
smearing          = interface-capture diffusion
```

This matters because a local-looking symptom can be caused by a coupled
contract violation.  A static-droplet velocity field, for example, is not just
a curvature test; it also probes whether pressure and surface tension share a
discrete force balance.

## Consequences

- Debugging by visual symptom alone can select the wrong module.
- A successful component test is insufficient when the failure requires two
  operators to balance each other.
- Verification tables should state which difficulty/failure axis they certify.
- Negative tests are legitimate when they demonstrate a forbidden coupling.

## Paper-Derived Rule

Classify a two-phase-flow failure by its coupled numerical mechanism, not by
the first field that looks wrong.
