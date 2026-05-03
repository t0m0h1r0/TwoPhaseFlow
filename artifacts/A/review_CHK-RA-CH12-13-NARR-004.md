# Review CHK-RA-CH12-13-NARR-004

Session: `CHK-RA-CH12-13-NARR-004`
Agent: ResearchArchitect
Branch: `ra-ch12-13-narrative-review-20260503`
Base: post-merge `main` at `15167bff`
Scope: `paper/sections/12*.tex`, `paper/sections/13*.tex`

## Verdict

PASS AFTER FIX. The post-merge rereview found no new structural objection to
the Chapter 12--13 narrative, but it did find two reviewer-visible scars left
by the previous root fixes. First, removing the obsolete lumped-PPE U6-b result
left U6 numbered as U6-a then U6-c, which made the deletion visible as an
editing artifact rather than a clean redesign around phase-separated PPE + HFE.
Second, Chapter 12 and Chapter 13 now shared the same result-table semantics,
but their column-header wrapping still differed. Both issues were fixed at the
paper-structure level: U6 now has contiguous subtest labels for the retained DC
and HFE primitives, and the Chapter 13 result table uses the same visual header
grammar as Chapter 12.

## Findings And Fixes

### RA-CH12-13-NARR-004-01: U6 retained an obsolete numbering scar

Finding: After the old high-density-ratio lumped-PPE subtest was removed from
the scored results, the retained HFE subtest was still labelled `U6-c`. A
reviewer reading the chapter would see U6-a followed by U6-c and infer either a
missing experiment or an unresolved editorial deletion. That weakened the
intended narrative: U6 is no longer a three-way comparison that preserves
lumped PPE as a candidate primitive; it is a two-part verification of DC guard
behavior and HFE extension accuracy for the phase-separated pressure stack.

Fix: Renamed the retained HFE subtest from `U6-c` to `U6-b` in the Chapter 12
summary table, U6 settings list, figure captions, and local verdict sentence.
No lumped-PPE scored row or standalone lumped-PPE table was restored.

### RA-CH12-13-NARR-004-02: Chapter 12 and 13 result tables still looked different

Finding: Chapter 12 and Chapter 13 used the same result-table columns after the
previous rereview, but Chapter 12 wrapped the two long headers while Chapter 13
left them on one line. Because these are now deliberately paired chapter-level
result summaries, the mismatch made the reader re-parse the table grammar and
undercut the requested cross-chapter consistency.

Fix: Updated Chapter 13's `tab:v_accuracy_summary` header to use the same
`\shortstack{期待・判定\\基準}` and `\shortstack{実測・観測\\値}` layout as
Chapter 12's `tab:verification_summary`.

## Validation

- `git diff --check` PASS.
- Targeted residue scan PASS: no stale `U6-c`, old lumped-PPE result row/table,
  old `fig:ch12_u6`, old Chapter 12/13 result-table wording pair, or unwrapped
  Chapter 13 result-table header remains in Chapter 12--13 paper targets.
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
