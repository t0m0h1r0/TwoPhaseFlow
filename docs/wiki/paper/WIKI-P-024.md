---
ref_id: WIKI-P-024
title: "Research Presentation Decks Need Claim-Proof Slides and Rendered Convergence"
domain: paper
status: ACTIVE
tags: [presentation, deck, review, visual_design, source_trace, convergence]
sources:
  - repo: https://github.com/t0m0h1r0/research-anomaly.git
    rev: 67ed252
    path: docs/wiki/cross-domain/WIKI-X-001_presentation_deck_review_loop.md
    description: "Claim-and-proof deck review loop for sponsor-facing research briefs"
  - repo: https://github.com/t0m0h1r0/research-backup.git
    rev: d17aa5c
    path: docs/wiki/presentation_refinement_practices.md
    description: "Presentation refinement practices from rendered review rounds"
depends_on:
  - "[[WIKI-M-035]]"
  - "[[WIKI-P-021]]"
  - "[[WIKI-P-022]]"
consumers:
  - domain: paper
    usage: "Use before creating, reviewing, or repairing research presentation decks"
  - domain: meta
    usage: "Use as a source-traced behavior packet for PresentationWriter prompt evolution"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Research Presentation Decks Need Claim-Proof Slides and Rendered Convergence

## Knowledge Card

Technical research decks should be designed as audience-facing claim-proof
systems, not as compressed manuscripts or decorative slide collections.

Each information slide needs:

- one primary assertion the audience can restate without speaker notes;
- one proof object below the lead line, such as a figure, chart, mechanism
  diagram, formula reading path, comparison table, or source-backed schematic;
- an explicit boundary around what the slide does not claim.

For TwoPhaseFlow decks, that boundary is the same scientific contract as the
paper: do not invent numerical results, benchmark status, literature claims,
SOTA language, physical interpretation, or algorithmic guarantees through
slide polish. Presentation style is a delivery layer over the
equation-to-discretization-to-code-to-experiment evidence chain.

## Reusable Practices

1. **Turn every slide into a claim-proof unit.**
   The title or lead line should say what the audience should believe after
   reading the slide. The dominant visual then proves or explains that message.
   If the proof object needs hidden context, either add labels/reading cues or
   split the slide.

2. **Prefer audience-action language over internal jargon.**
   Replace implementation labels, review IDs, and specialist shorthand with
   words that name the decision, comparison, or physical meaning. Keep exact
   terms when correctness requires them, but define them on first use or move
   supporting detail into notes/source maps.

3. **Make diagram and chart grammar visible.**
   Quantity-encoding visuals need axes, directions, units or state variables,
   and a one-line reading target. Architecture diagrams should follow one
   primary path and distinguish observed inputs, derived quantities, solver
   stages, excluded information, and outputs.

4. **Teach formulas through reading order.**
   Highlighting terms is not enough. Formula slides should tell the audience
   where to look first, what each term owns, how the update or diagnostic is
   assembled, and what decision changes after the expression is read. If a
   formula slide is trying to teach notation, intuition, and the takeaway at
   once, add a bridge slide or move detail to notes.

5. **Use comparison slides as diagnostic readouts.**
   Do not list method variants, models, or verification cases as catalogs.
   State what changes between rows/columns and what the comparison reveals:
   representation repair, conservation behavior, pressure split effect,
   stability condition, benchmark admission, or failure boundary.

6. **Keep visual drama inside a coherent, readable system.**
   Strong contrast, larger leads, staged emphasis, and localized dark moments
   can help, but abrupt background systems or full-dark dense technical slides
   often reduce readability. Use rendered review to validate theme choices,
   especially after formula, chart, or architecture changes.

7. **Record convergence by review round.**
   Each review round should name the audience-facing failure mode, severity,
   repair, render/layout result, forbidden-claim/source-fidelity checks, and
   stop/continue decision. Mechanical layout PASS is necessary, but contact
   sheets and full-size checks of clarity-critical slides are still required
   after substantial visual or structural edits.

## TwoPhaseFlow Deck Gate

Before final acceptance, check:

- Does every slide have one audience-facing message and one story role?
- Does every claim map to a paper section, wiki card, experiment result, or
  artifact, with unsupported claims marked TODO or removed?
- Do equation-heavy slides provide a reading path, not only symbols?
- Do diagrams expose the mathematical/physical locus they claim to explain:
  node, face, cell, graph, interface, pressure representative, or result path?
- Do comparison slides explain what the comparison teaches rather than naming
  internal case IDs only?
- Did rendered inspection confirm reading order, visual weight, text fit,
  chart/diagram labels, and export fidelity?
- Did the review loop close all High/Must-fix issues, or record explicit
  Do-not-fix / Human-review rationale?

## Anti-Patterns

- Treating theatrical style as new evidence.
- Allowing a beautiful visual to imply unsupported physics or performance.
- Fixing only the phrase named by a reviewer while leaving the same copy smell
  elsewhere in the deck.
- Drawing architecture as scattered labeled objects rather than one readable
  path.
- Showing formula terms or method names without a reading sequence.
- Adding slides to avoid prioritization instead of reducing cognitive load.
- Accepting automated layout checks as a substitute for rendered inspection.
