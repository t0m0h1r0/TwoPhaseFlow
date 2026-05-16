---
ref_id: WIKI-M-032
title: "Wiki Inventory Curation Uses Layered Evidence Passes"
domain: meta
status: ACTIVE
superseded_by: null
tags:
  - wiki_inventory
  - curation
  - retrieval_map
  - link_audit
  - stale_contracts
  - researcharchitect
sources:
  - path: artifacts/A/wiki_paper_code_curation_CHK-RA-WIKI-PAPER-CODE-001.md
    description: "Wiki/paper/code curation pass that produced this inventory practice"
  - path: docs/wiki/cross-domain/WIKI-X-041.md
    description: "Active retrieval map updated by the curation pass"
  - path: docs/wiki/INDEX.md
    description: "Index count and category synchronization target"
  - path: docs/wiki/meta/WIKI-M-031.md
    description: "Review artifact grammar used to close findings with fixes and validation"
depends_on:
  - "[[WIKI-M-007]]"
  - "[[WIKI-M-020]]"
  - "[[WIKI-M-031]]"
  - "[[WIKI-X-041]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-16
---

# Wiki Inventory Curation Uses Layered Evidence Passes

## Purpose

Wiki-wide inventory should not be treated as a linear read of every card as the primary method. A useful inventory pass layers mechanical checks, retrieval-front review, source triangulation, and targeted deep reads so stale operational claims can be fixed without deleting historically useful knowledge.

## Practice

1. Start from the active retrieval gate and `docs/wiki/INDEX.md`.
   - The retrieval gate shows what future agents will actually read first.
   - The index shows whether new cards, split cards, and category counts are synchronized.

2. Separate inventory from interpretation.
   - Inventory pass: counts, status distribution, latest IDs, active gate rows, broken links, stale path patterns, and obvious supersession notes.
   - Interpretation pass: decide whether each finding needs a rewrite, a new split card, a curation note, or only artifact documentation.

3. Use mechanical audits before and after edits.
   - Check wiki file count against index count.
   - Check indexed REF-IDs against files.
   - Check relative Markdown links inside `docs/wiki`.
   - Check active retrieval cards for old path names and stale operational front doors.

4. Classify staleness by status and retrieval role.
   - `ACTIVE` + retrieval-front stale claim: fix immediately or remove from active retrieval.
   - `REFERENCE` + historically correct but operationally stale claim: retain with an explicit curation note.
   - `SUPERSEDED` or supersession-linked claim: verify the successor is reachable from the index.

5. Triangulate wiki claims against paper and code before changing operational contracts.
   - Paper text can supply theorem, benchmark, and narrative intent.
   - Code/tests supply executable contracts and actual active paths.
   - Artifacts/ledger supply run-specific evidence and validation.

6. Choose split, rewrite, or note by retrieval behavior.
   - Split when a new concept deserves its own stable retrieval target.
   - Rewrite when an existing REF-ID is already the active front door for that concept.
   - Add a curation note when a broad theory card remains useful but should no longer be treated as the current operational source.

7. Preserve negative knowledge.
   - Do not delete historical cards merely because the active implementation moved.
   - Do not silently demote old claims; add a dated curation note or an explicit successor.
   - Do not update paper-facing wiki claims without checking the corresponding paper section and code route.

8. Close the loop in the same unit.
   - Record finding, fix, validation, and residual risk in the artifact or ledger.
   - Commit wiki/index/ledger changes as a coherent unit so future inventory passes can trust the provenance.

## Checklist

- Retrieval front: active retrieval gate, index category counts, latest IDs per domain.
- Mechanical audit: indexed files, unindexed files, missing files, broken relative wiki links.
- Stale scan: old source paths, deprecated result paths, superseded claims, "current" claims with old dates.
- Source triangulation: current paper sections, current code/test route, latest relevant artifact.
- Edit pattern: split new missing knowledge, rewrite active front doors, add curation notes to broad references.
- Validation: `git diff --check`, index/file count audit, relative-link audit, targeted stale-pattern scan.

## Anti-Patterns

- Full-reading every wiki card linearly as the primary strategy.
- Treating `REFERENCE` staleness as an active bug when the card is clearly curated.
- Letting index counts drift after adding or removing a card.
- Updating an active contract from memory without checking paper/code/artifact sources.
- Replacing historical knowledge with a narrower current answer when a curation note would preserve both.
