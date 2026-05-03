---
ref_id: WIKI-E-033
title: "Negative Knowledge Guards in Chapters 12--13"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [negative_result, verification, guards, chapter12, chapter13, v7, v10, dccd_pressure]
sources:
  - path: paper/sections/12u6_split_ppe_dc_hfe.tex
    description: "U6 guard for lumped PPE and HFE primitive role"
  - path: paper/sections/12u9_dccd_pressure_prohibition.tex
    description: "U9 DCCD-on-pressure prohibition"
  - path: paper/sections/13d_density_ratio.tex
    description: "V7 coupled-stack capillary/projection order limitation"
  - path: paper/sections/13e_nonuniform_ns.tex
    description: "V10 mass/shape axis split and fixed-grid limits"
  - path: paper/sections/13f_error_budget.tex
    description: "Integrated error-budget interpretation"
depends_on:
  - "[[WIKI-P-014]]"
  - "[[WIKI-T-079]]"
  - "[[WIKI-T-080]]"
  - "[[WIKI-E-032]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Negative Knowledge Guards

## Knowledge Card

Some of the most useful knowledge in Chapters 12--13 is negative: it tells the
project what must not be used as a shortcut.

| Result | Guard |
|---|---|
| U6 lumped-PPE high-density guard | Do not treat lumped smoothed-Heaviside PPE as the high-density production primitive. |
| U9 DCCD-on-pressure | Do not apply dissipative filtering to pressure; it breaks projection identity in the predicted way. |
| V7 sub-BDF2 coupled-stack slope | Do not describe V7 as pure BDF2 verification; it measures capillary pressure-jump/projection coupling. |
| V10-a shape limit | Do not hide fixed-grid phase/threshold and slot-resolution limits behind mass correction success. |
| V10-b reversal limit | Do not tune reinitialization or mass correction as if grid-scale folded filaments were reversible on a fixed Eulerian grid. |
| V9 local-epsilon switch | Do not claim improvement when the actual evidence is no-regression with the target stack. |

## Paper-Derived Rule

If a result rules out an attractive shortcut, keep it as a guard.  Do not soften
it into a mere failed test or tune it away without changing the measured
identity.
