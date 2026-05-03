---
ref_id: WIKI-P-014
title: "Verification Grammar: U-Series Certificates, V-Series Identity Tests, and Type-A/B/D"
domain: paper
status: ACTIVE
superseded_by: null
tags: [verification, paper, chapter12, chapter13, type_a, type_b, type_d]
sources:
  - path: paper/sections/12_component_verification.tex
    description: "U-series design map"
  - path: paper/sections/12h_summary.tex
    description: "U-series result table and negation-test grammar"
  - path: paper/sections/13_verification.tex
    description: "V-series verdict policy and Type taxonomy"
  - path: paper/sections/13f_error_budget.tex
    description: "V1--V10 integrated accuracy table"
depends_on:
  - "[[WIKI-P-005]]"
  - "[[WIKI-P-006]]"
  - "[[WIKI-E-013]]"
  - "[[WIKI-E-014]]"
  - "[[WIKI-E-032]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Verification Grammar

## Knowledge Card

Chapters 12 and 13 use the same table grammar, but not the same verification
semantics.

```text
U-series: certify a primitive in isolation.
V-series: test which identity survives after coupling.
```

This distinction is a paper-level contribution.  It prevents a component test
from being over-read as a full solver guarantee.

## U-Series Meaning

The U tests ask whether a primitive satisfies its local mathematical contract:

- spatial operator order,
- boundary/gauge consistency,
- HFE/DC primitive behavior,
- time-integrator standalone order,
- explicit prohibition tests such as DCCD-on-pressure.

## V-Series Meaning

The V tests ask what the coupled solver is actually measuring.  The Type labels
are part of that answer:

| Type | Meaning |
|---|---|
| Type-A | The correct criterion is the reduced experiment's identity, not the original idealized target. |
| Type-B | A structural algorithmic correction changes an axis into a passing contract. |
| Type-D | The conditional result matches a hard physical/discrete limit. |
| Stack diagnostic | A mode/switch is safe with the target stack but is not claimed as an improvement lever. |

## Paper-Derived Rule

When adding a new validation result, first classify the experiment's identity.
Only then choose pass/fail language.
