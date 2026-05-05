---
ref_id: WIKI-M-031
title: "Review Artifacts Close the Loop with Finding, Fix, and Validation"
domain: meta
status: ACTIVE
superseded_by: null
tags: [review_artifact, validation, findings, audit, evidence]
sources:
  - path: artifacts/A/review_CHK-RA-PAPER-005.md
    description: "Caption title/note review with policy, findings, commands, and results"
  - path: artifacts/A/review_CHK-RA-CH8-STRICT-REVIEW-001.md
    description: "Chapter 8 strict review finding/fix/validation grammar"
  - path: artifacts/A/review_CHK-RA-WIKI-CURATION-001.md
    description: "Wiki curation review and retention policy"
depends_on:
  - "[[WIKI-M-020]]"
  - "[[WIKI-X-041]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Review Artifact Grammar

## Knowledge Card

A useful review artifact is not just a list of complaints.  It closes a loop:

```text
scope -> verdict -> finding -> fix -> validation -> residual risk / retention
```

This grammar lets later ResearchArchitect passes distinguish accepted policy,
historical negative evidence, and merely local cleanup.

## Consequences

- Findings should be specific enough that the changed text/code can be audited.
- Fixes should state the new rule, not only the edited file.
- Validation commands and results make the artifact reusable after context
  compaction.
- Curation reviews should preserve historical cards or tests when they remain
  useful provenance, even if active retrieval changes.

## Paper-Derived Rule

Compile wiki knowledge from review artifacts only when the artifact contains a
closed finding-fix-validation chain or an explicit retention policy.
