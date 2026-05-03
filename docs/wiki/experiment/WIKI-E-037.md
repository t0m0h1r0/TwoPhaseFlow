---
ref_id: WIKI-E-037
title: "U6 Monolithic High-Density PPE Sweep Is a Guard, Not a Production Primitive"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter12, u6, ppe, defect_correction, hfe, density_ratio, negative_guard]
sources:
  - path: paper/sections/12u6_split_ppe_dc_hfe.tex
    description: "U6 DC omega guard and HFE primitive scope"
  - path: paper/sections/12h_summary.tex
    description: "U6 result rows and summary note excluding monolithic high-density sweep"
depends_on:
  - "[[WIKI-T-082]]"
  - "[[WIKI-T-099]]"
  - "[[WIKI-E-033]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# U6 Monolithic PPE Guard

## Knowledge Card

U6 does not certify monolithic smoothed-Heaviside high-density PPE as a production
primitive.  Its density-ratio sweep is a guard: it records residual stall and
supports the design decision to route high-density pressure work through
phase-separated PPE plus HFE.

The positive primitives in U6 are the DC relaxation guard and HFE field-extension
accuracy.

## Consequences

- Do not count high-density monolithic PPE convergence as a Chapter 12 success
  primitive.
- Residual improvement at aggressive `omega` is not a production-policy reversal.
- HFE accuracy is certified as a component, but full pressure-jump stack behavior
  is deferred to V6/V7/V9.
- U6 is both a positive primitive test and a negative route-selection guard.

## Paper-Derived Rule

When U6 is cited, say which half is being cited: HFE/DC primitive evidence or
monolithic-PPE guard evidence.
