---
ref_id: WIKI-P-021
title: "Whole-Scope Paper Review Reuses Local Review Gates"
domain: paper
status: ACTIVE
tags: [paper, review_prompt, whole_scope_review, readability, structure, citations]
sources:
  - path: docs/wiki/meta/WIKI-M-034.md
    description: "Paper review revisions reduce cognitive load rather than add decoration"
  - path: docs/wiki/paper/WIKI-P-020.md
    description: "Citation additions require claim-level source verification"
  - path: artifacts/A/review_CHK-RA-CH1-14-INT-001.md
    description: "Chapter 1--14 intuitive-math readability pass"
  - path: artifacts/A/review_CHK-RA-CITE-SURVEY-001.md
    description: "Source-verified related-work citation pass"
depends_on:
  - "[[WIKI-M-034]]"
  - "[[WIKI-P-020]]"
consumers:
  - domain: paper
    usage: "Use before drafting or executing a broad paper-review prompt"
  - domain: meta
    usage: "Use when updating ResearchArchitect paper-review task prompts"
compiled_by: ResearchArchitect
compiled_at: 2026-05-16
---

# Whole-Scope Paper Review Reuses Local Review Gates

## Knowledge Card

A whole-paper or broad-scope paper review should not be a larger version of a
single proofreading pass.  It should compose the local review gates that have
already proven useful:

- narrative and logical flow;
- intuitive reading of mathematical expressions;
- section and file responsibility;
- split-file prefix consistency;
- box/table/note necessity;
- removal of development-history wording from paper prose;
- claim-local citation verification;
- artifact, wiki, and validation closure.

The review prompt should make these gates explicit so that each chapter is not
only "checked" but brought to the same paper standard before the scope widens.

## Review Order

Use a widening loop:

```text
small unit -> chapter -> part -> whole target scope
```

Do not move to the next wider level while MAJOR-or-higher findings remain in
the current unit, unless the task records that the 20-round cap was reached and
lists the unresolved findings.

## Prompt Contract

A robust paper-review prompt should require:

1. a dedicated worktree and scoped branch;
2. unit decomposition before editing;
3. repeated review, edit, and re-review rounds;
4. explicit severity levels;
5. math-intuition checks that ask what each formula owns, updates, conserves,
   measures, or diagnoses;
6. file-size and section-responsibility checks before splitting;
7. prefix normalization after any split;
8. box/table/note audits based on reader benefit;
9. citation survey only when the exact manuscript claim needs support;
10. artifact and wiki updates for reusable lessons;
11. `git diff --check`, paper build when paper text changes, and final log
    scans for undefined citations/references and TeX warnings.

## Anti-Pattern

Avoid prompts that say only "review strictly" or "make it easier to read."
They invite local wording edits while missing the recurring causes of poor
paper quality: unclear mathematical ownership, mixed implementation history,
overgrown files, decorative boxes, stale references, and citations that are
related by keyword but not by claim.
