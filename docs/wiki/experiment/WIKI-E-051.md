---
ref_id: WIKI-E-051
title: "V3 Separates Pressure Accuracy from Spurious-Flow Monotonicity"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter13, v3, static_droplet, pressure_error, spurious_current]
sources:
  - path: paper/sections/13b_twophase_static.tex
    description: "V3 static droplet interpretation across pressure error, spurious current, and time saturation"
depends_on:
  - "[[WIKI-T-132]]"
  - "[[WIKI-E-034]]"
  - "[[WIKI-E-040]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# V3 Pressure vs Flow Metrics

## Knowledge Card

V3 static droplet verification deliberately separates pressure-jump accuracy
from spurious-flow behavior.  The pressure error after the long static run is
small, while spurious current is treated qualitatively rather than as a
quantitative upper-bound theorem.

The two axes are different:

```text
resolution axis : monotonic pressure/spurious-flow trend
time axis       : saturation behavior during a fixed run
```

## Consequences

- A pressure error below the reported percent-level bound does not by itself
  prove a universal spurious-current cap.
- N-axis monotonicity and time-axis saturation should not be collapsed into one
  metric.
- V3 peak spurious-current language and V5 final-time density-ratio metrics are
  not interchangeable.
- Static-droplet verification is a balanced-force sanity check, not the whole
  moving-interface validation.

## Paper-Derived Rule

When citing V3, keep pressure accuracy, spurious-current trend, and final-time
flow metrics as separate verification claims.
