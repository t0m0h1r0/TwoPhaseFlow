---
ref_id: WIKI-E-040
title: "V-Series Verdict Labels Encode Why a Result Counts"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter13, verdict, type_a, type_b, type_d, stack_diagnostic]
sources:
  - path: paper/sections/13_verification.tex
    description: "V verdict glyphs and Type-A/B/D plus stack diagnostic labels"
  - path: paper/sections/13f_error_budget.tex
    description: "V1--V10 accuracy budget and verdict-type aggregation"
depends_on:
  - "[[WIKI-P-014]]"
  - "[[WIKI-E-035]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# V-Series Verdict Labels

## Knowledge Card

Chapter 13 verdict labels are semantic.  A checkmark, triangle, Type-A, Type-B,
Type-D, and stack diagnostic each says why the result counts.

Type-A means the criterion was revised to match the implemented reduced identity.
Type-B means an explicit structural algorithm modification makes the target pass.
Type-D means the result aligns with a theoretical hard limit rather than meeting
an idealized accuracy target.  The §14 stack diagnostic is a no-regression/switch
diagnostic, not a criterion redefinition.

## Consequences

- A triangle can be a successful conditional verdict, not a failed test.
- Type-A is not weaker by default; it documents the correct reduced identity.
- Type-B should name the structural modification being credited.
- Type-D should name the hard limit being respected.
- Stack diagnostics must not be upgraded into broad production claims.

## Paper-Derived Rule

Read the verdict label as part of the experimental result.
