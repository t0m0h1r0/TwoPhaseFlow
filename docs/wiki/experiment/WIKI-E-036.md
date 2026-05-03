---
ref_id: WIKI-E-036
title: "U5 epsilon/h Window Is a Moment-Accuracy Gate, Not a Cosmetic Width"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter12, u5, heavi_side, delta, epsilon, moment_accuracy]
sources:
  - path: paper/sections/12u5_heaviside_delta.tex
    description: "U5 moment tests and epsilon/h sensitivity"
  - path: paper/sections/12h_summary.tex
    description: "U5 summary rows and saturation notes"
depends_on:
  - "[[WIKI-T-093]]"
  - "[[WIKI-E-035]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# U5 epsilon/h Window

## Knowledge Card

U5 shows that `epsilon/h` is an accuracy gate for interface moments.  The
smoothed delta's zero- and first-moment behavior is excellent near the adopted
support range, but insufficient support at small `c=epsilon/h` stalls the moment
accuracy.

The observed high-order/saturation behavior is not a generic double-precision
floor; the saturation level changes with `c`.

## Consequences

- `epsilon/h` cannot be tuned only for visual interface thickness.
- Small support (`c <= 1`) can stall moment recovery.
- `c in [1.5, 2]` is the validated moment-accuracy window in U5.
- Moment accuracy underpins later volume, CSF, and pressure-interface diagnostics.

## Paper-Derived Rule

Choose interface width as a quadrature/moment contract before treating it as a
geometry or aesthetics parameter.
