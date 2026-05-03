---
ref_id: WIKI-T-140
title: "CLS Third-Order Time Is for Geometry Robustness, Not Global Third Order"
domain: theory
status: ACTIVE
superseded_by: null
tags: [cls, tvd_rk3, time_integration, global_order, curvature]
sources:
  - path: paper/sections/07_time_integration.tex
    description: "Role of TVD-RK3 CLS transport inside a second-order coupled solver"
depends_on:
  - "[[WIKI-T-101]]"
  - "[[WIKI-T-125]]"
  - "[[WIKI-T-139]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# RK3 Geometry Robustness

## Knowledge Card

The CLS transport step can use TVD-RK3 without making the whole two-phase
solver third-order in time.  The coupled method remains second-order because
the Navier--Stokes/projection side is second-order.

The purpose of third-order CLS transport is more local:

```text
better transported geometry
lower curvature noise
less parasitic-current forcing
less frequent reinitialization pressure
```

## Consequences

- A second-order global time slope is not evidence that TVD-RK3 CLS failed.
- RK3 benefits may appear in curvature quality and parasitic currents rather
  than in headline global order.
- CLS time integration and NS time integration must be reported as coupled but
  distinct accuracy contributors.
- Replacing RK3 with a lower-order CLS step can damage interface geometry even
  if the NS side remains formally second-order.

## Paper-Derived Rule

Read TVD-RK3 in the paper as a geometry-robustness device inside a second-order
coupled time integrator.
