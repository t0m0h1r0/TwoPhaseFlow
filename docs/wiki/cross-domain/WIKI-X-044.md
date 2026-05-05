---
ref_id: WIKI-X-044
title: "Test Failure Retention Separates Live Contracts from Stale Probes"
domain: cross-domain
status: ACTIVE
superseded_by: null
tags: [tests, retention_policy, negative_evidence, regression, stale_probe]
sources:
  - path: artifacts/A/review_CHK-RA-SRC-TEST-001.md
    description: "Src test failure retention audit"
  - path: docs/memo/CHK-RA-SRC-MAJOR-ROUNDS-001_src_major_rounds.md
    description: "Side-effect audit and stale test expectation updates"
depends_on:
  - "[[WIKI-X-040]]"
  - "[[WIKI-X-041]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Test Retention Policy

## Knowledge Card

Failing tests should not be blindly fixed or deleted.  First classify what the
test is guarding:

```text
live contract with stale expectation -> keep and fix
wrong measurement of the right contract -> keep and repair metric
obsolete entangled probe -> discard only after a narrower retained test exists
```

This policy preserves negative evidence while preventing old probes from
blocking current paper-exact contracts.

## Consequences

- A stale hard-coded count is a test expectation bug, not evidence against the
  implementation.
- A test that measures the wrong field should be repaired, not deleted.
- A test may be discarded only when it no longer isolates its named regression
  and a direct retained test covers that regression.
- Threshold updates should stay below documented pre-fix drift or failure bands.

## Paper-Derived Rule

Treat test cleanup as evidence curation: keep live contracts, repair stale
measurements, and delete only non-isolating probes with replacement coverage.
