# CHK-RA-PAPER-004 — Appendix Format Review

Date: 2026-04-29
Worktree: `.claude/worktrees/ra-paper-strict-review-20260429`
Branch: `ra-paper-strict-review-20260429`
Source commit: `b8ffb56` (`paper: normalize appendix table typography`)
Main merge: not performed for this CHK; continue in the retained worktree.

## Trigger

User request: "付録についても同様にお願いします"

Scope:

- Appendix entry files and subfiles under `paper/sections/appendix*.tex`
- Appendix pressure-detail subfiles under `paper/sections/appD*.tex`

## Format Policy Applied

- Appendix numbered tables inherit the global centered, compact caption policy.
- Appendix numbered tables and inline technical tables use the same named table presets as the main chapters.
- Raw local numeric `\arraystretch` and `\tabcolsep` values are not used in appendix files.
- Dense appendix tables may opt into `\PaperTableDenseSetup` by name when width requires it.
- Appendix headings and captions follow the same Japanese numeric-spacing and reviewer-facing wording policy as the main chapters.

## Findings and Fixes

| ID | Finding | Fix |
|---|---|---|
| F01 | Appendix inline tables used local `\arraystretch` values from `1.2` to `1.4`, creating row-spacing drift. | Replaced inline table setup with `\PaperTableSetup`. |
| F02 | Appendix numbered tables still had local row-spacing overrides despite the global table preset. | Removed local overrides and let global table setup apply. |
| F03 | The PPE solver comparison table became slightly overfull under the unified default width policy. | Applied the named dense preset `\PaperTableDenseSetup` to that table. |
| F04 | Appendix headings and captions retained compact forms such as `2次元`, `2段階`, `4次`, and `vs`. | Normalized to `2 次元`, `2 段階`, `4 次`, and Japanese comparison wording. |

## Files Reviewed and Updated

- `paper/sections/appendix_ccd_coef_s2.tex`
- `paper/sections/appendix_ccd_impl_s1.tex`
- `paper/sections/appendix_ccd_impl_s2.tex`
- `paper/sections/appendix_ccd_impl_s3.tex`
- `paper/sections/appendix_ccd_impl_s4.tex`
- `paper/sections/appendix_hfe_verify.tex`
- `paper/sections/appendix_interface_s2.tex`
- `paper/sections/appendix_nondim_details.tex`
- `paper/sections/appendix_numerics_solver_s1.tex`
- `paper/sections/appendix_numerics_solver_s3.tex`
- `paper/sections/appendix_numerics_solver_s4.tex`
- `paper/sections/appendix_numerics_solver_s5.tex`
- `paper/sections/appendix_ppe_pseudotime.tex`
- `paper/sections/appendix_verification_details.tex`

## Reproduction Commands

```bash
files=$(rg --files paper/sections | rg '/(appendix|appD)' | sort)
rg -n '\\renewcommand\{\\arraystretch\}\{[0-9]|\\setlength\{\\tabcolsep\}\{[0-9]' $files
rg -n 'justification=RaggedRight|singlelinecheck=false|\\caption\{.*( vs |\\textit\{vs\.)' paper/preamble.tex $files
rg -n '(^\\(section|subsection|subsubsection|paragraph)|\\caption\{).*([0-9０-９]+(次元|次|段階|つ|倍|方向)|[A-Z][0-9]-|[0-9]D)' $files
cd paper && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
rg -n 'LaTeX Warning|Package .* Warning|Overfull \\hbox|Underfull \\hbox|Missing character|Undefined control sequence|Emergency stop|Fatal error|^!' main.log
git diff --check
make lint-ids
```

## Results

- Raw local numeric table spacing audit: 0 residual hits.
- Left/ragged caption and `vs` caption audit: 0 residual hits.
- Appendix heading/caption numeric-spacing audit: 0 residual hits.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: OK.
- `paper/main.pdf`: 234 pages.
- Final `main.log` diagnostic grep: 0 hits.
- `git diff --check`: OK.
- `make lint-ids`: OK.

## SOLID-X

Paper and review documentation only. No `src/twophase/` or production class/module boundary change.
