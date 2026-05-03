---
ref_id: WIKI-E-046
title: "U4 Distinguishes HJ Gradient Recovery from DGR Width Closure"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter12, u4, eikonal, dgr, reinitialization, epsilon_eff]
sources:
  - path: paper/sections/12u4_ridge_eikonal_reinit.tex
    description: "U4 Godunov Eikonal band-gradient recovery and DGR one-step width correction"
depends_on:
  - "[[WIKI-T-110]]"
  - "[[WIKI-T-115]]"
  - "[[WIKI-T-116]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# U4 Two Reinit Primitives

## Knowledge Card

U4 verifies two different primitives:

```text
U4-a : Godunov Eikonal pseudo-time recovery of |grad phi| ~= 1
U4-b : DGR one-step correction of epsilon_eff / epsilon*
```

The first is an iterative Hamilton--Jacobi recovery path with band-gradient
residuals.  The second is a geometric width-rescaling correction that drives an
initial width ratio from `2.0` to approximately `1.0000033` in one step.

## Consequences

- Eikonal iteration count and DGR width-ratio correction are separate metrics.
- A good DGR ratio does not prove the same thing as an Eikonal band-gradient
  residual.
- U4 validates primitive behavior, not the full moving-interface coupled stack.
- The `epsilon_eff` diagnostic is operationally tied to DGR, not merely to
  plotting the interface band.

## Paper-Derived Rule

When reading U4, keep HJ distance-gradient recovery and DGR profile-width
closure as two distinct reinitialization certificates.
