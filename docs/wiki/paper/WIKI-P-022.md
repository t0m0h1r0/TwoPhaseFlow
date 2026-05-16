---
ref_id: WIKI-P-022
title: "Formula-Heavy Paper Sections Need Ownership-Ledger Prose"
domain: paper
status: ACTIVE
tags: [paper, math_readability, equations, narrative, review]
sources:
  - path: artifacts/A/review_CHK-RA-CH1-14-INT-001.md
    description: "Chapter 1--14 intuitive-math readability pass and review gate"
  - path: paper/sections/01b_classification_roadmap.tex
    description: "Chapter-spanning reading spine for formulas"
  - path: paper/sections/11_full_algorithm.tex
    description: "Algorithm chapter reframed around interface, momentum, and pressure/work ledgers"
depends_on:
  - "[[WIKI-M-034]]"
  - "[[WIKI-P-021]]"
consumers:
  - domain: paper
    usage: "Use before revising formula-heavy manuscript sections"
  - domain: theory
    usage: "Use when translating mathematical contracts into paper prose"
compiled_by: ResearchArchitect
compiled_at: 2026-05-16
---

# Formula-Heavy Paper Sections Need Ownership-Ledger Prose

## Knowledge Card

When a section is hard to read because it contains many equations, the first
fix is usually not to delete equations or add casual analogies.  The better
paper move is to tell the reader what each formula is responsible for.

Before presenting a dense formula block, establish the reading ledger:

- what object is owned by this equation;
- whether the object is transported, reconstructed, measured, constrained, or
  diagnosed;
- what changes after the equation is applied;
- what output is passed to the next stage;
- what invariant, residual, or benchmark quantity lets the reader know the
  equation did its job.

This turns formulas from a sequence of symbols into a traceable update story.

## Four Formula Roles

Classify formula-heavy prose by role:

1. **Transport ledger**: equations that move a conserved or primary state.
2. **Geometry ledger**: equations that measure interface position, distance,
   normals, curvature, or fitted-grid geometry.
3. **Constraint/work ledger**: equations that impose incompressibility,
   pressure jumps, capillary work, wall constraints, or reaction spaces.
4. **Diagnostic ledger**: equations and tables that verify convergence,
   conservation, residual decrease, or benchmark agreement.

If a paragraph mixes these roles without naming the shift, readers lose the
thread even when every equation is individually correct.

## Placement Rule

Use short bridge prose at chapter or section entrances:

```text
This section's equations should be read as:
input -> owned update -> output handed to the next section/stage.
```

Do not repeat the same explanation before every equation.  Put the bridge at
the point where the reader chooses how to read the next block.  Inside the
block, use only small reminders such as "the transported quantity", "the
geometry measurement", or "the pressure-work residual" when the role changes.

## Review Gate

For each formula-heavy unit, ask:

- Can a reader say what the equation owns or updates?
- Can a reader distinguish transported state from geometric measurement?
- Can a reader distinguish pressure/constraint work from capillary or
  diagnostic quantities?
- Does the section say which quantity is preserved, reduced, or passed forward?
- Does the next section consume the output named here?

If the answer is no, revise the surrounding prose before changing notation.
