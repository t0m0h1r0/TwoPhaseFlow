---
ref_id: WIKI-E-038
title: "U9 Negation Pass: A Rule Violation Can Be a Successful Test"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter12, u9, negation_test, dccd, pressure, operator_policy]
sources:
  - path: paper/sections/12u9_dccd_pressure_prohibition.tex
    description: "U9 DCCD-on-pressure prohibition and spatial violation map"
  - path: paper/sections/12h_summary.tex
    description: "U9 bullet verdict convention in Chapter 12 summary"
depends_on:
  - "[[WIKI-T-079]]"
  - "[[WIKI-T-089]]"
  - "[[WIKI-E-033]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# U9 Negation Pass

## Knowledge Card

U9 passes by proving a prohibited operation fails in the predicted way.  Applying
DCCD to pressure is intentionally measured as a violation, and the observed error
growth supports the operator policy.

This is why the summary uses a bullet verdict rather than a checkmark: the test
passes, but the candidate operation is rejected.

## Consequences

- A successful negation test is not approval to use the tested operation.
- DCCD-on-pressure error is spatially structured, not harmless random noise.
- Pressure-gradient operator policy is informed by a measured failure mode.
- Verdict glyphs in Chapter 12 encode test type, not just pass/fail status.

## Paper-Derived Rule

For prohibition tests, the artifact being validated is the rule, not the
forbidden method.
