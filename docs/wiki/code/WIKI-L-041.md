---
ref_id: WIKI-L-041
title: "YAML Route Flags Make Numerical Contracts Auditable"
domain: code
status: ACTIVE
tags: [yaml, route_flags, reproducibility, gpu]
sources:
  - path: docs/02_ACTIVE_LEDGER.md
  - path: paper/sections/14_benchmarks.tex
---

# YAML Route Flags Make Numerical Contracts Auditable

## Claim

When a route changes the mathematical contract, the YAML must say so.  Hidden
defaults are not acceptable for projection, pressure representative, transport,
or variational-curvature routes.

## Effective Knowledge

- Pressure snapshot representatives such as Hodge/phase pressure belong in
  YAML output configuration.
- Projection/DC capacity, debug residual diagnostics, snapshot cadence, and
  GPU route assumptions must be visible before long runs.
- Short-run configs are not disposable clutter when they encode acceptance
  gates for a later expensive run.

## Negative Knowledge

Launching remote jobs without proving `TWOPHASE_USE_GPU=1`, or enabling a new
physics route without an explicit config knob, makes the result difficult to
audit and easy to misinterpret.

## Implication

Every new physics route should answer: what YAML key selects it, what diagnostic
proves it is active, and what short gate must pass before a long run.
