---
ref_id: WIKI-T-079
title: "Operator Eligibility by Field Regularity: Smoothness Before Formal Order"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ccd, fccd, uccd6, regularity, operator_policy, pressure_jump, cls]
sources:
  - path: paper/sections/04_ccd.tex
    description: "Three-point compactness motivation and CCD/FCCD/UCCD6 family split"
  - path: paper/sections/06_scheme_per_variable.tex
    description: "Per-variable operator selection policy"
  - path: paper/sections/06c_fccd_advection.tex
    description: "FCCD face-flux and face-jet use for advection/BF consistency"
  - path: paper/sections/12h_summary.tex
    description: "DCCD-on-pressure negative verification"
depends_on:
  - "[[WIKI-T-046]]"
  - "[[WIKI-T-055]]"
  - "[[WIKI-T-061]]"
  - "[[WIKI-T-062]]"
  - "[[WIKI-T-069]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Operator Eligibility By Field Regularity

## Knowledge Card

The paper's operator policy is not "use the highest-order scheme everywhere".
It is:

```text
formal order is admissible only when the field is regular enough
for that stencil and output locus.
```

The resulting assignment is:

| Field | Regularity | Eligible operator |
|---|---|---|
| Smooth bulk velocity | Smooth away from interface band | CCD/UCCD6/FCCD variants. |
| CLS `psi` | Steep tanh, bounded, conservative carrier | FCCD face-flux transport, not raw nodal CCD. |
| Pressure across interface | Jump discontinuity | Face-flux + GFM/IIM/HFE, not uncorrected nodal CCD. |
| Density/viscosity | Step-like algebraic fields | Low-order algebraic/face/corner rules, not CCD. |
| Interface-band velocity gradients | Kinked or phase-switched | Low-order one-sided/interface-band closure. |

## Why It Matters

CCD's sixth-order compactness is valuable because it gives high resolution in a
three-point footprint.  But the same compactness becomes harmful if the stencil
crosses a jump, kink, or saturated CLS profile.  The paper repeatedly treats
unqualified high order as a category error.

## Paper-Derived Rule

Before changing a discretization, answer two questions:

1. Is the field smooth enough for the chosen stencil?
2. Is the operator output located where the consuming equation expects it?

If either answer is no, raising formal order is not a fix.
