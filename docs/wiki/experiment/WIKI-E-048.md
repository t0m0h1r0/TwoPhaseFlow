---
ref_id: WIKI-E-048
title: "U6 Omega Sweep Is a Relaxation Guard Before Split PPE"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter12, u6, defect_correction, omega, split_ppe, density_ratio]
sources:
  - path: paper/sections/12u6_split_ppe_dc_hfe.tex
    description: "U6-a DC omega relaxation sweep and its non-production role for high density ratios"
depends_on:
  - "[[WIKI-T-126]]"
  - "[[WIKI-T-131]]"
  - "[[WIKI-E-037]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# U6 Omega Guard

## Knowledge Card

U6-a is a relaxation-guard experiment for defect correction.  The high-density
lumped-PPE cases mostly stall, with only restricted relaxed settings converging,
so the result is intentionally not promoted to the production primitive.

The production path is instead the later split stack:

```text
FCCD / UCCD6 / HFE / pressure-jump / phase PPE / DC
```

## Consequences

- U6-a is negative knowledge about monolithic high-density relaxation, not a
  failed requirement for the final solver.
- `omega` is a convergence guardrail for a diagnostic primitive.
- High-density validation must be read through the split PPE/HFE stack rather
  than the early lumped-PPE sweep.
- The experiment prevents an attractive but unstable shortcut from being
  mistaken for the production algorithm.

## Paper-Derived Rule

Read U6-a as a guard on DC relaxation behavior before the split PPE closure,
not as the final high-density pressure primitive.
