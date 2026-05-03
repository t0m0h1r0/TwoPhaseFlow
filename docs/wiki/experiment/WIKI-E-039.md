---
ref_id: WIKI-E-039
title: "V-Series Uses Reduced Stack Paths, Not One Monolithic Solver Path"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter13, v_series, reduced_stack, verification_path, operator_stack]
sources:
  - path: paper/sections/13_verification.tex
    description: "V-test operator-stack subsets and four reduced verification paths"
depends_on:
  - "[[WIKI-E-035]]"
  - "[[WIKI-E-034]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# V-Series Reduced Stack Paths

## Knowledge Card

The V-series does not run every test on one monolithic final solver path.  It
uses reduced stack subsets matched to the question being tested:

```text
V1/V2: single-phase reduction
V3/V4/V5/V8: two-phase BF reduction with Neumann FVM PPE
V6/V7/V9: pressure-jump phase-separated stack subset
V10-a/b: NS-non-coupled CLS advection path
```

This makes the V-series a structured integration matrix rather than a single
benchmark ladder.

## Consequences

- Metrics are comparable only after checking the path subset.
- V3/V5/V8 do not validate pressure-jump PPE because they use Neumann BF
  reduction.
- V6/V7/V9 are the relevant pressure-jump stack subset tests.
- V10 validates CLS transport behavior without NS/PPE coupling.

## Paper-Derived Rule

Before interpreting a V-test result, identify which reduced operator stack was
active.
