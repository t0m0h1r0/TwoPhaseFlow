# Review CHK-RA-CH12-13-NARR-003

Session: `CHK-RA-CH12-13-NARR-003`
Agent: ResearchArchitect
Branch: `ra-ch12-13-narrative-review-20260503`
Base: post-merge `main` at `810091e4`
Scope: `paper/sections/12*.tex`, `paper/sections/13*.tex`

## Verdict

PASS AFTER FIX. The user comments were valid reviewer concerns, not surface
style preferences. Chapter 12 had two result-looking tables at the beginning
and end, Chapter 13 still described the U design table as if it shared the
same result-table grammar, and U6-b made a retired high-density-ratio lumped
PPE path look like a component achievement. The fix separates table roles and
aligns the pressure narrative with Chapters 4--11: Chapter 12 opens with a
design/dependency map, Chapter 12 and 13 each have one result table in the
same grammar, and U6 now verifies DC/HFE primitives for the phase-separated
PPE stack rather than preserving lumped PPE as a scored subtest.

## Findings And Fixes

### RA-CH12-13-NARR-003-01: Chapter 12 opening and closing tables duplicated roles

Finding: `tab:U_summary` at the Chapter 12 opening and
`tab:verification_summary` at the closing both looked like result summaries.
Even after the headers were aligned, the reader still encountered nearly the
same kind of table twice, first before the tests and then again after them.
This weakened the narrative because the chapter appeared to reveal results
before building the evidence.

Fix: Recast `tab:U_summary` as a `検証設計マップ`: each U row now states the
primitive being fixed and the Chapter 13 destination. All numerical outcomes
are collected only in `tab:verification_summary`, which is now explicitly
described as Chapter 12's sole result summary.

### RA-CH12-13-NARR-003-02: Chapter 12 and 13 result-table grammars were still semantically mixed

Finding: Chapter 13's result table referred to both `tab:U_summary` and
`tab:verification_summary` as if both were result tables with the same grammar.
After the opening table became a design map, that wording would have recreated
the same ambiguity from the other side.

Fix: Updated the Chapter 13 result-table caption to compare only
`tab:v_accuracy_summary` with Chapter 12's actual result table
`tab:verification_summary`. It now states explicitly that `tab:U_summary` is
not a result table.

### RA-CH12-13-NARR-003-03: U6-b made lumped PPE look like a scored primitive

Finding: U6-b scored the high-density-ratio lumped/smoothed-Heaviside PPE
sweep as a conditional result. This conflicted with the Chapter 9 and Chapter
11 narrative, where the standard high-density-ratio pressure path is
phase-separated pressure-jump PPE + HFE + DC, and lumped PPE is only a low
density-ratio comparator/path-selection diagnostic. Keeping U6-b in the result
table made the obsolete path look like a component that the paper still needed
to defend.

Fix: Removed U6-b as a scored result row and removed the standalone U6-b table
from the paper narrative. U6 now verifies two production-relevant primitives:
DC relaxation guard behavior and HFE 1D/2D extension accuracy. The lumped PPE
high-density-ratio sweep remains only as explanatory design context: it is the
reason not to use lumped PPE for high-density-ratio production, not a Chapter
12 achievement.

## Validation

- `git diff --check` PASS.
- Targeted paper residue scan PASS: no scored `U6-b` row,
  `tab:U6_n_rho_sweep`, old `fig:ch12_u6`, `lumped--PPE`, or old Chapter 12
  result-table heading remains in Chapter 12--13 paper targets.
- Targeted notation scan PASS:
  `\epsilon`, `\eps`, bare `\kappa`, `\hat{n}`, `\mathbf{u}`, `\nabla p`,
  `\nabla H`, and bare `\nabla\cdot` absent from Chapter 12--13 targets.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` PASS
  in `paper/`; output `main.pdf`, 243 pages.
- Remaining log notes observed: pre-existing underfull hbox in
  `sections/09f_pressure_summary.tex:57` and a float-only page warning around
  Chapter 12 after table/figure movement; neither affects references or build
  success.

## SOLID-X

Paper/audit-only change. No production code boundary changed, no tested code
deleted, no FD/WENO/PPE fallback introduced, and no experiment data or figures
were modified.
