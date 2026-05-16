# CHK-RA-CH1-14-INT-001 Review

## Scope

User request:

- Create a new worktree.
- Strictly review Chapters 1--14 with renewed emphasis on whether the paper is easy to understand and whether equation-heavy content is explained intuitively.
- Revise the manuscript, not as a superficial pass but in the form most likely to make the reader understand.

Worktree:

- `.claude/worktrees/codex-ra-ch1-14-intuitive-review-20260516`
- Branch: `codex/ra-ch1-14-intuitive-review-20260516`

## Review Gate

The review did not treat "add an explanation paragraph" as the goal.  The gate was:

1. Can the reader say what object a formula owns or updates?
2. Can the reader distinguish transported quantities, geometric measurement quantities, and pressure/work reaction quantities?
3. Does each chapter tell the reader what to track before the algebra becomes dense?
4. Does the explanation preserve scientific contracts without changing equations, parameters, solver policy, or validation claims?

## Main Finding

Chapters 1--14 already contained many local explanations, but the explanations were uneven.  Chapter 11 had a strong "ledger" model from the previous pass, while other chapters often explained correct formulas locally without first giving the reader a stable way to read the formulas.

The best repair was therefore not to decorate individual equations.  The paper needed:

- a chapter-spanning reading spine in the roadmap, so a reader knows what to track in each chapter before entering the algebra;
- chapter-specific "how to read the formulas" bridges where the intuitive object changes;
- no change to equation meaning or validation scope.

## Changes

### Cross-Chapter Spine

Added `1--14章の数式読解ロードマップ` to `paper/sections/01b_classification_roadmap.tex`.

This gives each chapter one reader task:

- Ch1: read the difficulty as ledger mismatch.
- Ch2: read symbols as the shared dictionary.
- Ch3: separate transported amount and measuring coordinate.
- Ch4: read CCD as compact local consistency, not formula collection.
- Ch5: read reinitialization as geometric projection, not physical motion.
- Ch6: read operator choice by field smoothness and output location.
- Ch7: read time integration as stiffness/constraint sorting.
- Ch8: read pressure as a face-space reaction.
- Ch9: read PPE as a reaction construction that handles discontinuities.
- Ch10: read nonuniform grids as coordinate maps with physical measures.
- Ch11: read the algorithm as ownership transfer across ledgers.
- Ch12: read U-tests as component contract checks.
- Ch13: read V-tests as integrated failure-mode diagnostics.
- Ch14: read benchmarks through preservation, initial response, boundedness, and shape evolution.

### Chapter-Level Bridges

Added chapter-specific intuitive bridges in:

- `paper/sections/01_introduction.tex`
- `paper/sections/02_governing.tex`
- `paper/sections/03_levelset.tex`
- `paper/sections/04_ccd.tex`
- `paper/sections/05_reinitialization.tex`
- `paper/sections/06_scheme_per_variable.tex`
- `paper/sections/07_time_integration.tex`
- `paper/sections/08_collocate.tex`
- `paper/sections/09_ccd_poisson.tex`
- `paper/sections/10_grid.tex`
- `paper/sections/11_full_algorithm.tex`
- `paper/sections/12_component_verification.tex`
- `paper/sections/13_verification.tex`
- `paper/sections/14_benchmarks.tex`

These bridges are intentionally prose-first.  They state what the reader should track before the formulas branch into detailed definitions, discretizations, or validation tables.

## Non-Scope

No equation meaning, physical parameter, numerical algorithm, CFL, damping, smoothing, tolerance, fallback behavior, validation result, experiment YAML/result data, or production source code was changed.

## Validation

- `git diff --check`: PASS
- `make -B -C paper`: PASS, generated `paper/main.pdf` with 279 pages
- Final `paper/main.log` diagnostic scan: PASS
  - no LaTeX/package/class warnings
  - no overfull/underfull boxes
  - no undefined references/citations/control sequences
  - no fatal errors or raw TeX errors

## Commits

- `bb8d4dfe chore: start ch1-14 intuitive review`
- `bb6e6207 paper: add intuitive math guides for chapters 1-7`
- `7b657425 paper: add intuitive reading spine for chapters 1-14`
