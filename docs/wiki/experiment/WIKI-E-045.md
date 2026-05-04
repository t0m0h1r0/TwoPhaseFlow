---
ref_id: WIKI-E-045
title: "U3 Separates Nonuniform Operator Order from Metric Guardrails"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter12, u3, nonuniform_grid, fccd, ridge_eikonal, metrics]
sources:
  - path: paper/sections/12u3_nonuniform_spatial.tex
    description: "U3 verdicts for non-uniform CCD/FCCD order and Ridge-Eikonal D1-D4 metrics"
depends_on:
  - "[[WIKI-T-094]]"
  - "[[WIKI-T-113]]"
  - "[[WIKI-T-130]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# U3 Nonuniform Split Verdict

## Knowledge Card

U3 has two different verification axes:

```text
operator order axis : CCD and FCCD still converge at their design order
metric guard axis   : Ridge-Eikonal D1-D4 corrections behave as theory predicts
```

The `D4` activation at stretched grids is not a failure; it is the expected
chain-rule correction firing at small magnitude while the uniform-grid limit
returns zero.

## Consequences

- Non-uniform spatial verification is not complete with MMS slopes alone.
- Metric diagnostics can pass by being zero in the uniform limit and active in
  the stretched case.
- FCCD face order on non-uniform grids is checked separately from projection
  face-adjoint consistency.
- U3 supplies preconditions for later non-uniform V tests, not integrated NS
  validation by itself.

## Paper-Derived Rule

Read U3 as a two-axis gate: design-order preservation for operators and
guardrail behavior for the non-uniform metric machinery.
