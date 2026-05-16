---
ref_id: WIKI-P-020
title: "Paper Citation Additions Need Claim-Level Source Verification"
domain: paper
status: ACTIVE
tags: [paper, citations, literature_survey, review, bibliography]
sources:
  - path: paper/sections/01b_classification_roadmap.tex
    description: "Related-work placement for CLS, balanced force, and consistent mass-momentum transport"
  - path: paper/sections/03_levelset.tex
    description: "Chapter-local CLS and high-order compact CLS citation placement"
  - path: paper/sections/09b1_split_ppe.tex
    description: "Split PPE positioning against pressure-correction literature"
  - path: paper/sections/11_full_algorithm.tex
    description: "Common-flux ledger connection to mass-momentum consistency literature"
  - path: artifacts/A/review_CHK-RA-CITE-SURVEY-001.md
    description: "Source-verification table for the cited papers"
depends_on:
  - "[[WIKI-M-034]]"
consumers:
  - domain: paper
    usage: "Use before adding literature references to the manuscript"
  - domain: meta
    usage: "Use as a review gate for citation-survey tasks"
compiled_by: ResearchArchitect
compiled_at: 2026-05-16
---

# Paper Citation Additions Need Claim-Level Source Verification

## Knowledge Card

Citation work should not add a bibliography padding layer.  Add a reference
only when three gates are all satisfied:

1. the paper exists as a peer-reviewed or otherwise authoritative source, with
   DOI, venue, authors, year, and pages verified;
2. the source content supports the exact manuscript claim being made;
3. the citation is placed at the claim site, not only in a broad literature
   paragraph.

## Placement Rule

Use the citation to clarify the manuscript's intellectual neighborhood:

- cite the original method when the manuscript uses that method as a baseline;
- cite a neighboring method when the manuscript shares a problem setting but
  uses a different closure, and state the distinction in the prose;
- cite a benchmark or validation paper only where the corresponding benchmark,
  diagnostic, or acceptance criterion is discussed.

Do not cite a paper merely because it uses the same broad keywords.  If the
relationship is "same problem, different mechanism," write that distinction
explicitly.

## Verification Record

Each citation-survey edit should leave an artifact table with:

- candidate paper;
- evidence URL or DOI page;
- verified content match;
- manuscript location where it was used;
- reason for excluding any plausible but unnecessary candidates.

Close with `git diff --check`, a full paper build, and a final log scan for
undefined citations/references and TeX warnings.
