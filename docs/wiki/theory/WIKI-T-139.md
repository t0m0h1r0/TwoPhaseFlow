---
ref_id: WIKI-T-139
title: "CLS Reinitialization Pseudo-Time CFL Is Not Physical Delta t"
domain: theory
status: ACTIVE
superseded_by: null
tags: [cls, reinitialization, pseudo_time, cfl, ridge_eikonal]
sources:
  - path: paper/sections/07_time_integration.tex
    description: "Distinction between physical time-step limits and pseudo-time reinitialization constraints"
depends_on:
  - "[[WIKI-T-103]]"
  - "[[WIKI-T-116]]"
  - "[[WIKI-T-140]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Pseudo-Time Is Not Physical Time

## Knowledge Card

CLS reinitialization has its own pseudo-time stability story.  An explicit
Hamilton--Jacobi/parabolic reinit iteration may need hyperbolic and parabolic
pseudo-time limits, but a one-shot Ridge--Eikonal reconstruction has no
physical-time CFL.

This means the solver time step and the reinit internal iteration count are
different contracts:

```text
physical Delta t : advances the coupled NS/CLS problem
pseudo-time tau  : internal distance-profile recovery, if used
```

## Consequences

- A Ridge--Eikonal reinit call should not be rejected because it lacks an
  explicit pseudo-time CFL loop.
- Iterative Eikonal convergence tolerances do not apply to one-shot
  reconstruction in the same way.
- Physical time-step diagnostics must not mix reinit iteration stability with
  capillary, advection, buoyancy, or discrete-spectrum limits.
- Reinit frequency is a geometry-quality policy, not the physical integrator
  time step itself.

## Paper-Derived Rule

Separate physical `Delta t` constraints from reinitialization pseudo-time
constraints before diagnosing CLS stability.
