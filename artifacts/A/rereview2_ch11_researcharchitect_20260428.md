# Chapter 11 Second Re-Review — ResearchArchitect

Date: 2026-04-28
Worktree: `/Users/tomohiro/Downloads/TwoPhaseFlow-ch11-review`
Branch: `worktree-ra-ch11-review`
Reviewed closure commit: `59d2929 fix(ch11): close rereview findings`

## Routing

- ResearchArchitect classification: FULL-PIPELINE
- HAND-01 route: PaperWorkflowCoordinator -> PaperReviewer
- Scope: current Chapter 11 as compiled from `paper/main.tex`: `paper/sections/12_component_verification.tex` and `paper/sections/12u*.tex`, plus directly cited `experiment/ch12/exp_U*.py` support scripts.
- Verdict: PASS (0 FATAL, 0 MAJOR, 0 MINOR)

## Closure Verdict

- R-M1 closed: U6-c no longer hides the 2D median degradation. The parent dashboard marks U6-c as conditional with all reported slopes `5.99 / 5.05 / 3.21`, and the detailed U6 subsection explicitly separates the 1D stencil pass from the 2D geometric-band diagnostic.
- R-M2 closed: U8 Layer C expectations now match between paper and script. Both describe the B/C behavior as effective first order from explicit cross-term / ADI splitting.
- R-m1 closed: U6 script docstrings and console summaries no longer advertise stale `ch13`, `1D ~= 7.0`, `2D ~= 6.33 / 5.79`, or "negative @ N>=64" claims.
- No new Chapter 11 paper/script contradiction was found in this pass.

## Evidence Checked

- `paper/sections/12_component_verification.tex`: U6-c dashboard row and 18 checkmark + 4 triangle + 1 bullet recount.
- `paper/sections/12u6_split_ppe_dc_hfe.tex`: U6-c caption, figure caption, and evaluation paragraph.
- `experiment/ch12/exp_U6_split_ppe_dc_hfe.py`: U6 docstring and `print_summary()` paper-facing text.
- `paper/sections/12u8_time_integration.tex`: U8-d B/C first-order known-degradation statement and conditional verdict.
- `experiment/ch12/exp_U8_time_integration_suite.py`: Layer C docstring and implementation-level expected slope.

## Mechanical Checks

- Targeted stale-pattern grep: no hits for old U6/U8 claims (`expected slope 1.5`, `partial recovery`, `1D ~= 7.0`, `6.33 / 5.79`, `ch13 high`, old U6-c full-pass/count wording).
- Syntax check: `PYTHONDONTWRITEBYTECODE=1 ... -m py_compile experiment/ch12/exp_U[1-9]_*.py` passed.
- LaTeX: `latexmk -xelatex -interaction=nonstopmode main.tex` reported all targets up-to-date.

## Final Assessment

The Chapter 11 rereview findings are fully closed. The chapter is now internally auditable for the reviewed scope: U6-c is conservatively classified as conditional, U8-d script and paper expectations agree, and the support-script paper-facing text no longer contains stale targets.
