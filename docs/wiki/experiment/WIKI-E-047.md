---
ref_id: WIKI-E-047
title: "U5 Delta Moments Certify Surface-Force Measure Support"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter12, u5, delta, moment_accuracy, surface_force]
sources:
  - path: paper/sections/12h_summary.tex
    description: "U5 delta moment results and their interpretation as surface-force measure support"
depends_on:
  - "[[WIKI-T-106]]"
  - "[[WIKI-T-110]]"
  - "[[WIKI-E-036]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# U5 Delta Moment Certificate

## Knowledge Card

U5 is a measure-support test for the regularized interface delta.  Its key
numbers are moment residuals, not visual band thickness: U5-a reports zero- and
first-moment errors near `1e-11`, and U5-b reaches machine-level zero-moment
closure for a representative `c=2, N=128` case.

The certified object is:

```text
regularized delta support -> surface-force integral measure
```

## Consequences

- U5 supports CSF force accuracy through moment closure, not by simply showing
  a smooth interface plot.
- The `epsilon/h` window matters because it controls quadrature of the
  interface measure.
- Moment accuracy is prerequisite evidence for balanced surface forcing, but
  not a full coupled-flow validation by itself.
- A visually acceptable delta band can still be rejected if the moment
  residuals fail.

## Paper-Derived Rule

Use U5 as a delta-measure certificate for surface forcing, not as a cosmetic
interface-width check.
