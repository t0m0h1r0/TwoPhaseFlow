---
ref_id: WIKI-E-049
title: "U9 DCCD Pressure Violation Is an Asymptotic Order-Gap Test"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter12, u9, dccd, pressure, negation_test, asymptotic_order]
sources:
  - path: paper/sections/12u9_dccd_pressure_prohibition.tex
    description: "U9 negation test showing pressure-space DCCD as destructive perturbation"
depends_on:
  - "[[WIKI-T-123]]"
  - "[[WIKI-T-133]]"
  - "[[WIKI-E-038]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# U9 Pressure-Space Negation

## Knowledge Card

U9 succeeds by making the forbidden operation visibly bad: applying DCCD in
pressure space creates an `O(h^2)` perturbation while the compliant reference
approaches the floor.  The growing ratio is therefore an asymptotic order-gap
certificate, not an instability surprise.

The tested rule is:

```text
DCCD is allowed for appropriate transported/differentiated fields
DCCD is prohibited on the pressure variable used by projection closure
```

## Consequences

- A large violation/reference ratio is the expected pass condition for this
  negative test.
- The fixed DCCD perturbation scale matters because the reference error falls
  toward machine precision.
- Pressure filtering is not harmless smoothing; it changes the projection
  unknown and breaks the adjoint/jump closure.
- U9 should be cited when preventing "just filter the pressure" fixes.

## Paper-Derived Rule

Use U9 as a prohibition certificate: DCCD-on-pressure is a destructive
operator mismatch, not a stabilizing filter.
