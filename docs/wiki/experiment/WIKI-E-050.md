---
ref_id: WIKI-E-050
title: "V1 Measures the Implemented CCD/PPE Path, Not the Old FFT Proxy"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter13, v1, single_phase_ns, ppebuilder, implementation_identity]
sources:
  - path: paper/sections/13a_single_phase_ns.tex
    description: "V1 single-phase NS verification and replacement of the old FFT spectral proxy"
depends_on:
  - "[[WIKI-T-129]]"
  - "[[WIKI-E-040]]"
  - "[[WIKI-E-044]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# V1 Implemented-Path Identity

## Knowledge Card

V1 is not a nostalgic comparison to the old FFT spectral proxy.  The paper
uses it as an implementation-identity test for the actual CCD/PPEBuilder path
that the solver runs.

The useful reading is:

```text
V1-a : spatial path through implemented CCD/FVM-PPE components
V1-b : time path through the standard projection implementation
```

## Consequences

- The observed `2.00` spatial slope is interpreted through the implemented FVM
  PPE path, not through an ideal spectral projection.
- Old-pressure handling in V1-b belongs to the standard projection path; it is
  not a hidden predictor shortcut.
- A V1 result cannot be used to claim properties of a removed FFT proxy.
- V1 is a wiring/identity certificate before two-phase complications are added.

## Paper-Derived Rule

Read V1 as evidence about the current implementation path, not about an older
standalone spectral reference code.
