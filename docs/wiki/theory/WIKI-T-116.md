---
ref_id: WIKI-T-116
title: "Iterative Eikonal Stopping Rules Do Not Apply to One-Shot Ridge-Eikonal"
domain: theory
status: ACTIVE
superseded_by: null
tags: [reinitialization, eikonal, ridge_eikonal, stopping_criteria, virtual_time]
sources:
  - path: paper/sections/05_reinitialization.tex
    description: "Implementation guide distinguishing one-shot reconstruction from iterative Eikonal solvers"
depends_on:
  - "[[WIKI-T-103]]"
  - "[[WIKI-T-113]]"
  - "[[WIKI-T-115]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# One-Shot vs Iterative Reinit

## Knowledge Card

The paper separates two reinitialization modes:

```text
Ridge-Eikonal / xi-SDF / FMM path : one-shot distance reconstruction
Godunov/WENO-HJ Eikonal path      : virtual-time iteration
```

Residual tolerances, maximum pseudo-time steps, and Hamilton--Jacobi CFL
settings apply only to the iterative path.  They are comparison/diagnostic
rules, not hidden loops inside the one-shot Ridge--Eikonal route.

## Consequences

- Do not tune `N_tau` to improve a reconstruction path that has no virtual-time
  loop.
- Physical `Delta t` is not constrained by one-shot reinit pseudo-time CFL.
- If an implementation uses iterative Eikonal, it must report residual and step
  cap separately.
- Algorithm descriptions should state which reinit path is active.

## Paper-Derived Rule

Attach pseudo-time stopping criteria only to pseudo-time solvers; keep one-shot
Ridge--Eikonal reconstruction audited by geometry, mass, and seed admissibility.
