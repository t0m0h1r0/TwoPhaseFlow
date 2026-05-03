---
ref_id: WIKI-E-035
title: "U-Series Component Verification Is Not Integrated Physics Validation"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter12, component_verification, integration_verification, cpu_reference, u_series, v_series]
sources:
  - path: paper/sections/12_component_verification.tex
    description: "Chapter 12 purpose, tier map, CPU-reference policy, and U-to-V design map"
  - path: paper/sections/12h_summary.tex
    description: "Chapter 12 limits and bridge from U primitives to V integrated tests"
depends_on:
  - "[[WIKI-P-014]]"
  - "[[WIKI-E-033]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# U-Series Component Verification

## Knowledge Card

The U-series certifies numerical primitives, not the integrated physical solver.
It is intentionally CPU-fixed and component-level: individual operators,
redistancing primitives, HFE/DC pieces, time integrators, and prohibition tests
are measured against mathematical expectations.

The V-series then rechecks how those primitives behave when coupled in the full
Predictor--PPE--Corrector pipeline.

## Consequences

- A U-test pass is not a long-time NS stability proof.
- CPU values are canonical references for primitive precision.
- GPU/CuPy behavior belongs to later integrated/operational validation.
- The U-to-V bridge table is a dependency map, not a duplicate results table.
- Any primitive interaction not present in U must be judged in V.

## Paper-Derived Rule

Read U-results as admission tickets to integrated testing, not as final physical
claims.
