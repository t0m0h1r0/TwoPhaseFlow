---
ref_id: WIKI-T-126
title: "Defect Correction Accuracy Lives in the High-Order Residual"
domain: theory
status: ACTIVE
superseded_by: null
tags: [defect_correction, residual, high_order_operator, fixed_point, solver]
sources:
  - path: paper/sections/07_time_integration.tex
    description: "Defect correction as common high-order residual fixed-point principle"
depends_on:
  - "[[WIKI-T-005]]"
  - "[[WIKI-T-082]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# DC Residual Contract

## Knowledge Card

Defect correction solves a high-order system by evaluating the defect with the
high-order operator `A_H` and solving only the correction equation with cheaper
`A_L`:

```text
r = b - A_H x
A_L delta = r
x <- x + omega delta
```

The low-order operator controls the convergence path and cost.  It does not
define the fixed point, provided the outer residual is reduced against `A_H`.

## Consequences

- Replacing `A_L` changes convergence behavior, not the intended high-order
  discrete equation.
- Stopping criteria must monitor `b - A_H x`, not only the correction solve.
- A cheap preconditioner is admissible only while it remains a good error
  reducer for `A_H`.
- DC is a common principle for PPE and viscous Helmholtz systems, not a
  pressure-only trick.

## Paper-Derived Rule

Judge defect-correction accuracy by the high-order residual; judge the
low-order operator by convergence and robustness.
