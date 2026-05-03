# CHK-RA-FRONT-ABST-001 — Front Matter / Abstract Review

## Scope

- Request: `retry` / `Execute ResearchArchitect` / 表紙と要旨を現行の論文内容に則して見直す。
- Worktree: `.claude/worktrees/ra-frontmatter-abstract-review-20260503`
- Branch: `ra-frontmatter-abstract-review-20260503`
- Target files: `paper/sections/00_abstract.tex`, `paper/preamble.tex`

## Verdict

PASS AFTER REVISION.

The previous front matter still described an older paper headline:
Crank--Nicolson viscosity, AB2+IPC global second order, DCCD pressure usage,
and a low-density smoothed-Heaviside / FD-direct PPE path as if it were the
main pressure design.  The current manuscript instead centers the §14 stack:
FCCD conservative CLS, UCCD6, Balanced-Force face-jet coupling, pressure-jump
phase-separated FCCD-PPE, HFE, DC `k=3`, and explicit verification gates for
V7 / V10 / physical benchmarks.

## Findings And Fixes

1. **Cover title and subtitle lagged the current contribution.**
   Replaced the old CCD / CLS / DCCD / projection headline with a title that
   names high-order compact schemes, Conservative Level Set, Balanced Force,
   and pressure-jump phase-separated PPE.

2. **Cover method table carried stale contracts.**
   Replaced `Crank--Nicolson` viscosity and DCCD-on-pressure phrasing with
   TVD-RK3, IMEX-BDF2/EXT2, implicit-BDF2 + DC, IPC pressure increments, and
   an explicit pressure-prohibition caveat for DCCD.

3. **Pressure closure hierarchy was inverted.**
   Reframed the standard headline as pressure-jump phase-separated FCCD-PPE +
   HFE + DC `k=3`; smoothed-Heaviside one-field PPE is now described as a
   low-density / reduced-verification path rather than the main stack.

4. **Abstract overclaimed completed physical validation.**
   Rewrote the abstract to separate completed U/V verification from remaining
   gates: V7 final slope `1.04` as Type-D, nonuniform moving-interface CLS,
   long-time fully coupled NS moving interfaces, Prosperetti dispersion,
   Hysing terminal velocity, and Rayleigh--Taylor growth-rate validation.

5. **PDF metadata was stale.**
   Updated `pdftitle` from the merged placeholder to the current English title.

## Validation

- `git diff --check` PASS.
- Targeted stale-frontmatter scan PASS for old cover/abstract contracts.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` PASS.
  Output: `paper/main.pdf`, 243 pages.
- Remaining LaTeX notes are outside this patch: existing underfull hbox in
  `sections/09f_pressure_summary.tex:57` and the Chapter 12 float-only page.

## SOLID Audit

[SOLID-X] Paper and audit artifact only.  No production boundary changed, no
tested code deleted, and no FD/WENO/PPE fallback introduced.
