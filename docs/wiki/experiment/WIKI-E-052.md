---
ref_id: WIKI-E-052
title: "V6 Pressure-Correction Ratio Is Auxiliary, Not Laplace Error"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter13, v6, density_ratio, pressure_correction, laplace_error, split_stack]
sources:
  - path: paper/sections/13d_density_ratio.tex
    description: "V6 density-ratio static droplet interpretation and auxiliary pressure-correction diagnostic"
depends_on:
  - "[[WIKI-T-129]]"
  - "[[WIKI-E-034]]"
  - "[[WIKI-E-040]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# V6 Auxiliary Pressure Ratio

## Knowledge Card

V6 validates high-density static-droplet robustness of the split coupled stack:

```text
FCCD / UCCD6 / HFE / pressure jump / phase PPE / DC
```

The pressure-correction ratio reported there is an auxiliary diagnostic.  It
must not be reinterpreted as the absolute Young--Laplace pressure error.

## Consequences

- No-blowup density-ratio cases certify the split stack, not ordinary
  CCD/FVM-PPE alone.
- CLS volume drift near machine precision is a separate conservation signal.
- The pressure-correction ratio is useful for projection behavior, but it is
  not the Laplace pressure target itself.
- Comparing V6 pressure diagnostics to V3 pressure error requires matching the
  metric definition first.

## Paper-Derived Rule

Use V6's pressure-correction ratio as an auxiliary projection diagnostic, not
as a substitute for the Laplace pressure-error metric.
