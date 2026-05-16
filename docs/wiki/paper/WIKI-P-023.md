---
ref_id: WIKI-P-023
title: "Paper Placement Review Keeps Front Matter and Chapters Responsible"
domain: paper
status: ACTIVE
tags: [paper, review, placement, front_matter, narrative, terminology]
sources:
  - path: artifacts/A/review_CHK-RA-PAPER-COVER-14P2-001.md
    description: "Cover-to-14.2 review that added a chapter-placement gate"
  - path: docs/wiki/paper/WIKI-P-021.md
    description: "Whole-scope paper review gate stack"
  - path: docs/wiki/paper/WIKI-P-022.md
    description: "Formula-heavy sections need ownership-ledger prose"
depends_on:
  - "[[WIKI-P-021]]"
  - "[[WIKI-P-022]]"
consumers:
  - domain: paper
    usage: "Use when reviewing whether a claim, detail, box, or term belongs in its current chapter"
compiled_by: ResearchArchitect
compiled_at: 2026-05-16
---

# Paper Placement Review Keeps Front Matter and Chapters Responsible

## Knowledge Card

Broad paper review should ask not only whether a sentence is correct, but
whether it belongs where it currently appears.

Placement failures often look like good information in the wrong room:

- a cover page acting like a verification dashboard;
- an abstract using internal gate labels before those labels are defined;
- a benchmark chapter repeating derivation vocabulary that belongs in the
  methods or verification chapter;
- a box containing normal exposition that would read better as body prose;
- a result table carrying process history instead of a claim-local result.

Correctness does not excuse poor placement. If the reader sees a technical
detail before they know why it matters, the detail increases cognitive load
even when it is true.

## Placement Gate

For each paragraph, formula bridge, table, figure, or box, ask:

1. Does this belong in the current chapter?
2. Would the same information be clearer in a preceding definition chapter, a
   later verification chapter, a benchmark section, an appendix, an artifact,
   or a wiki card?
3. Is this front matter summarizing the paper, or preloading method and result
   details before the reader has the map?
4. Is the terminology appropriate for the reader's current stage, or does it
   expose an internal implementation/review label too early?
5. If moved or shortened, what local bridge remains so the current paragraph
   still makes sense?

## Repair Pattern

When placement is wrong, prefer one of three repairs:

- **Compress in place** when the current section needs only orientation.
- **Move or defer** when the details are valid but belong to a later method,
  verification, or benchmark responsibility.
- **Delete from paper body** when the text is development history, review
  process, or implementation bookkeeping better kept in artifacts.

For front matter, keep the research question, contribution spine, achieved
evidence, and remaining limitations. Leave detailed scheme inventories,
verification labels, and benchmark numerics to the body unless they are
essential to the abstract's main claim.
