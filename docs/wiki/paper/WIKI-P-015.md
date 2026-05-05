---
ref_id: WIKI-P-015
title: "Chapters 1-13 Use Failure-Mode to Contract Traceability"
domain: paper
status: ACTIVE
superseded_by: null
tags: [paper, traceability, failure_modes, contracts, chapters_1_13]
sources:
  - path: paper/sections/01_introduction.tex
    description: "Problem statement and four difficulty classes"
  - path: paper/sections/06_scheme_per_variable.tex
    description: "Variable-specific scheme routing"
  - path: paper/sections/11_full_algorithm.tex
    description: "Full algorithm contract ordering"
  - path: paper/sections/13_verification.tex
    description: "Integrated verification grammar"
depends_on:
  - "[[WIKI-X-042]]"
  - "[[WIKI-P-014]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Failure-Mode Traceability

## Knowledge Card

Chapters 1-13 form a traceability chain:

```text
failure mode
-> numerical contract
-> discretization choice
-> one-step algorithm position
-> verification identity
```

This chain is more important than the chronological order of methods.  For
example, a capillary-wave failure should be traced through curvature, jump sign,
face locus, PPE/corrector identity, and the V-series identity before it is
treated as a time-step issue.

## Consequences

- Paper edits should preserve the route from motivation to verification.
- Wiki cards should prefer contract names over chapter-local prose labels.
- A component method is not accepted until its place in the full-step ordering
  and verification grammar is clear.
- Appendix proofs should be linked back to the main-text contract they support.

## Paper-Derived Rule

When compiling paper knowledge into the wiki, store the contract trace, not
only the local derivation.
