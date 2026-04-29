# CHK-RA-PAPER-003 — Table and Caption Typography Review

Date: 2026-04-29
Worktree: `.claude/worktrees/ra-paper-strict-review-20260429`
Branch: `ra-paper-strict-review-20260429`
Source commit: `3bf49cf` (`paper: unify table and caption typography`)
Main merge: not performed for this CHK; continue in the retained worktree.

## Trigger

User concern:

- 表における、文字サイズ、行間サイズ、横幅、等の揺れ
- 図表タイトルが中央にないこと、行間サイズが大きいこと

## Format Policy Applied

- Captions are globally centered, not locally left-ragged.
- Caption text uses compact line spacing via `font={small,stretch=0.94}` and a compact vertical gap via `skip=4pt`.
- Tables use named presets instead of ad-hoc local numeric settings:
  - `\PaperTableSetup`: default table body size and row spacing.
  - `\PaperTableDenseSetup`: dense summaries that need tighter width/height control.
  - `\PaperTableExtraDenseSetup`: exceptional multi-row chapter summaries that otherwise exceed page height.
- Chapter files must not introduce raw local numeric `\arraystretch` or `\tabcolsep` settings.
- Float-heavy dense verification blocks may use float pages when that is clearer than forcing mixed text/float pages.

## Findings and Fixes

| ID | Finding | Fix |
|---|---|---|
| F01 | Global captions were configured with `RaggedRight` and `singlelinecheck=false`, so titles were not centered. | `paper/preamble.tex` now centers captions globally and keeps single-line captions centered. |
| F02 | Tables used scattered numeric row spacing such as `0.92`, `1.0`, `1.1`, `1.2`, `1.5`, making visual rhythm hard to predict. | Replaced with policy macros or shared macro values. |
| F03 | Dense tables mixed local `\footnotesize`, `\scriptsize`, and column padding decisions without a named rationale. | Replaced with dense and extra-dense presets so the exception is visible and reproducible. |
| F04 | V10 verification floats became clearer as dedicated float-page material after caption/table spacing normalization. | Changed the relevant V10 table/figure floats to page floats. |

## Files Reviewed

- `paper/preamble.tex`
- `paper/sections/01_introduction.tex` through `paper/sections/15_conclusion.tex`
- `artifacts/A/paper_format_policy_CHK-RA-PAPER-002.md`

## Reproduction Commands

```bash
files=$(find paper/sections -maxdepth 1 -type f \( -name '01*.tex' -o -name '02*.tex' -o -name '03*.tex' -o -name '04*.tex' -o -name '05*.tex' -o -name '06*.tex' -o -name '07*.tex' -o -name '08*.tex' -o -name '09*.tex' -o -name '10*.tex' -o -name '11*.tex' -o -name '12*.tex' -o -name '13*.tex' -o -name '14*.tex' -o -name '15*.tex' \) | sort)
rg -n '\\renewcommand\{\\arraystretch\}\{[0-9]|\\setlength\{\\tabcolsep\}\{[0-9]' $files
rg -n 'justification=RaggedRight|singlelinecheck=false' paper/preamble.tex $files
cd paper && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
rg -n 'LaTeX Warning|Package .* Warning|Overfull \\hbox|Underfull \\hbox|Missing character|Undefined control sequence|Emergency stop|Fatal error|^!' main.log
git diff --check
make lint-ids
```

## Results

- Raw local numeric table spacing audit: 0 residual hits.
- Left-ragged caption configuration audit: 0 residual hits.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: OK.
- `paper/main.pdf`: 236 pages.
- Final `main.log` diagnostic grep: 0 hits.
- `git diff --check`: OK.
- `make lint-ids`: OK.

## SOLID-X

Paper and review documentation only. No `src/twophase/` or production class/module boundary change.
