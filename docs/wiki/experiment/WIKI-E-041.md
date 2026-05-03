---
ref_id: WIKI-E-041
title: "V7 Coupled-Stack Slope Is Interface-Band Limited, Not BDF2 Failure"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter13, v7, type_d, capillary, pressure_jump, time_accuracy]
sources:
  - path: paper/sections/13_verification.tex
    description: "V7 reclassification rationale and RCA summary"
  - path: paper/sections/13f_error_budget.tex
    description: "V7 coupled-stack effective slope in the accuracy budget"
depends_on:
  - "[[WIKI-T-103]]"
  - "[[WIKI-E-040]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# V7 Coupled-Stack Slope

## Knowledge Card

V7's sub-2 time slope is recorded as a Type-D coupled-stack limit, not as a
failure of BDF2 itself.  The paper isolates the dominant factor to the capillary
pressure-jump / affine FCCD projection behavior in the low-regularity interface
band near `psi ~= 0.5`.

U8 independently verifies the pure time integrators.  V7 asks a different
question: what effective order remains when capillary jump projection, interface
transport, and HFE/FCCD stack components are coupled.

## Consequences

- Do not compare V7 directly to the U8 pure BDF2 slope.
- Reinitialization count and reference-depth changes do not remove the observed
  interface-band limit.
- Turning off surface tension collapses the error, confirming capillary coupling
  as the relevant axis.
- V7 is a coupled-stack diagnostic of the full pressure-jump path.

## Paper-Derived Rule

For coupled capillary stack tests, judge the effective stack slope, not the
standalone integrator order.
