---
ref_id: WIKI-M-033
title: "Paper Review Revisions Should Reduce Cognitive Load, Not Add Decoration"
domain: meta
status: ACTIVE
superseded_by: null
tags:
  - paper_review
  - paper_revision
  - cognitive_load
  - box_audit
  - section_split
  - naming_convention
  - validation
sources:
  - path: docs/02_ACTIVE_LEDGER.md
    description: "CHK-RA-CH11-002 through CHK-RA-CH11-005 paper readability, split, prefix, and box-audit records"
  - path: paper/sections/11_full_algorithm.tex
    description: "Chapter 11 understanding model and operator-notation demotion"
  - path: paper/sections/11b1_full_timestep.tex
    description: "Full timestep procedure demoted from a mega-box to normal narrative flow"
  - path: paper/sections/10a1_2d_tracking_grid.tex
    description: "Tracking-grid closure demoted from a mega-box while preserving technical content"
  - path: paper/sections/09f_pressure_summary.tex
    description: "Pressure-closure condition demoted from a visual wrapper while preserving the reference label"
depends_on:
  - "[[WIKI-M-031]]"
  - "[[WIKI-M-032]]"
  - "[[WIKI-P-018]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-16
---

# Paper Review Revisions Should Reduce Cognitive Load

## Purpose

Paper review is not cosmetic cleanup.  A useful revision changes the reader's
route through the argument: what they must track, which object owns each
quantity, which result is a contract, and which detail is only support.
Visual emphasis, file splitting, and naming conventions are helpful only when
they reduce that cognitive load.

## Practice

1. Review for the reader's task, not for local polish.
   - Before editing, name what the reader must understand after the section.
   - Good framing often says what object is owned, what output is passed forward,
     and what invariant is being closed.
   - If a mathematical section feels hard only because every equation has equal
     visual weight, add a reading model before changing formulas.

2. Treat boxes as scarce reader aids.
   - Keep boxes for short definitions, warnings, algorithms, result summaries,
     and acceptance criteria that a reader should be able to find instantly.
   - Demote boxes that merely introduce a section, restate adjacent prose,
     decorate a table, or wrap a long continuous argument.
   - Avoid mega-boxes and nested box flows.  They make the paper look organized
     while interrupting the actual narrative.
   - When demoting a box, preserve labels, equations, table content, and
     cross-reference targets unless the label itself is obsolete.

3. Split files only when size and responsibility both justify it.
   - A long file is not automatically wrong; split when the file contains
     distinct reader responsibilities or natural section boundaries.
   - Do not split tightly coupled derivations where the reader must keep one
     variational or algebraic object in view.
   - After splitting, verify that `paper/main.tex`, current source maps, wiki
     metadata, and project maps point to the new files.

4. Normalize names immediately after splitting.
   - If one logical prefix is split into multiple parts, number the first part
     too: `09b1`, `09b2`, not `09b`, `09b2`.
   - Keep lexical order, input order, and reader order aligned.
   - Historical ledgers and artifacts can keep old paths as provenance; current
     retrieval and build references should use the new paths.

5. Preserve scientific contracts while improving presentation.
   - Presentation edits must not change equation meaning, physical parameters,
     solver policy, validation thresholds, or algorithm acceptance boundaries.
   - If a box or split contains a contract, move the contract into normal prose
     or a smaller retained box before removing the wrapper.
   - A readability revision is complete only when a reviewer can explain what
     became easier to understand.

6. Close every paper revision with the same validation grammar.
   - `git diff --check`
   - targeted scans for stale names or box counts when relevant
   - `make -B -C paper`
   - final `paper/main.log` diagnostic scan for warnings, overfull/underfull
     boxes, undefined references/citations/control sequences, and fatal errors
   - ledger entry with scope, decision rule, validation, and explicit non-scope

## Checklist

- Reader model: what should the reader track after this section?
- Box gate: definition, warning, algorithm, result, or acceptance criterion?
- Flow gate: does the box interrupt a continuous derivation or large procedure?
- Split gate: size plus distinct content responsibility?
- Name gate: first split file numbered consistently?
- Reference gate: build inputs, current maps, wiki metadata, and source maps updated?
- Contract gate: equations and physical/numerical policy unchanged?
- Validation gate: diff check, targeted scan, paper build, log scan, ledger.

## Anti-Patterns

- Adding emphasis because a section feels difficult, without deciding what the
  reader needs to understand.
- Wrapping an entire algorithm or derivation in a box and calling it clearer.
- Splitting files only by line count while leaving one conceptual unit scattered.
- Leaving `09b`, `09b2`-style mixed prefixes after a split.
- Updating current references but ignoring source maps or wiki metadata.
- Treating paper presentation cleanup as permission to change equations,
  thresholds, solver routes, or validation claims.
