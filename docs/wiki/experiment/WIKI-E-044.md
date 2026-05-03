---
ref_id: WIKI-E-044
title: "U1 Is an Operator-Family Contract, Not a Single CCD Test"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter12, u1, ccd, dccd, fccd, uccd6, operator_family]
sources:
  - path: paper/sections/12u1_ccd_operator.tex
    description: "U1 operator-family verdicts for CCD, DCCD, FCCD, and UCCD6"
depends_on:
  - "[[WIKI-T-117]]"
  - "[[WIKI-T-119]]"
  - "[[WIKI-T-120]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# U1 Operator-Family Contract

## Knowledge Card

U1 is not just "CCD convergence."  It verifies an operator family:

```text
U1-a CCD d1/d2 periodic slopes
U1-b DCCD Nyquist transfer value
U1-c FCCD face value/grad fourth order
U1-d UCCD6 nodal RHS behavior
```

The point is that Chapter 12 certifies each operator's distinct role before the
integrated stacks consume them.  A pass in one row cannot substitute for a pass
in another row because the operators occupy different numerical channels.

## Consequences

- U1 should be read as a four-primitive interface for later chapters.
- FCCD fourth order is a face-evaluation result, not a CCD sixth-order result.
- DCCD is verified by transfer-function behavior, not by the same MMS metric as
  CCD.
- UCCD6 super-convergence in the MMS is a favorable observation, not a new
  baseline order contract.

## Paper-Derived Rule

Use U1 to certify the operator family member that will be consumed later; do
not collapse CCD/DCCD/FCCD/UCCD6 into one generic "high-order operator" pass.
