# Chapter 11 Re-Review — ResearchArchitect

Date: 2026-04-28
Worktree: `/Users/tomohiro/Downloads/TwoPhaseFlow-ch11-review`
Branch: `worktree-ra-ch11-review`
Base review: `artifacts/A/review_ch11_researcharchitect_20260428.md`

## Routing

- ResearchArchitect classification: FULL-PIPELINE
- HAND-01 route: PaperWorkflowCoordinator -> PaperReviewer
- Scope: current Chapter 11 as compiled from `paper/main.tex`: `paper/sections/12_component_verification.tex` and `paper/sections/12u*.tex`, plus the directly cited `experiment/ch12/exp_U*.py` support scripts.
- Verdict: FAIL (0 FATAL, 2 MAJOR, 1 MINOR)

## Post-Fix Status

- Fix status: all listed R-M1 / R-M2 / R-m1 findings addressed in this worktree.
- Fix scope: U6-c is now a conditional 1D-stencil + 2D-geometric-band result; U8 Layer C script expectations now match the paper's effective first-order criterion; U6 support-script docstrings and console summaries now mirror the current Chapter 11 table.
- Verification completed before closure: targeted stale-pattern grep, Python syntax check for U6/U8 scripts, and LaTeX build.

## Closure Check Against Previous Review

- F-1 chapter identity / numbering: closed. `paper/main.tex` comments, Chapter 11 header, and roadmap now consistently identify component verification as current §11.
- F-2 stale A3 implementation paths: closed. The previously nonexistent endpoints were replaced with existing `src/twophase/...` paths.
- F-3 U6 split-PPE mislabeling: closed at the paper level. U6 is now described as lumped-PPE + DC + HFE evidence, with split-PPE used only as downstream motivation.
- F-4 U7 match/mismatch interpretation: closed. The paper now describes operator-pairing mismatch at fixed `rho_l/rho_g = 1000`.
- M-1 U5 moment mismatch: closed. The paper now uses delta moments and the logistic implementation path.
- M-2 U8-d contradictory paper verdict: mostly closed in the paper, but not fully closed in the support script; see R-M2.
- M-3 U9 script/paper mismatch: closed. The pressure field, Laplacian diagnostic, and floor-limited ratio behavior now match the script.
- M-4 U1-c wall/periodic contradiction: closed. The paper now attributes the fourth-order result to periodic face endpoint evaluation.
- M-5 paper figure regeneration path: closed. All U scripts now define `PAPER_FIG` and call `save_figure(..., also_to=PAPER_FIG)`.
- m-1 summary count: closed. The table summary now reports 19 checkmarks + 3 triangles + 1 negation = 23 subtests.
- m-2 old support-file references: closed for `Paper ref` headers; no stale `§12c/§12d/§12e` support-file refs remain.

## MAJOR

### R-M1 — U6-c HFE verdict hides an internal 2D median-order failure

- `paper/sections/12_component_verification.tex:114`: parent dashboard reports U6-c as `HFE 1D / 2D`, design `$6 / 6$`, measured `$5.99 / 5.05$`, verdict `\checkmark`.
- `paper/sections/12u6_split_ppe_dc_hfe.tex:74`: U6-c caption says HFE is a standalone MMS for the extrapolation stencil.
- `paper/sections/12u6_split_ppe_dc_hfe.tex:76`: the same caption says the 2D `max` rate is 4--5 due to interface-grid alignment.
- `paper/sections/12u6_split_ppe_dc_hfe.tex:77`: the caption says 2D `med` is sixth-order design.
- `paper/sections/12u6_split_ppe_dc_hfe.tex:89`: the actual reported slopes are 1D `5.99`, 2D `max 5.05`, 2D `med 3.21`.
- `paper/sections/12u6_split_ppe_dc_hfe.tex:116`: the evaluation downgrades 2D median to "3 次以上" but still concludes the HFE design specification is satisfied with `\checkmark`.

Issue: U6-c currently gives three incompatible readings: the dashboard says 2D HFE meets design `6`, the detailed caption says the median statistic is sixth-order design, and the table reports median slope `3.21`. If median is part of the 2D HFE acceptance criterion, U6-c cannot be a full checkmark. If median is diagnostic-only, the dashboard and caption must say that explicitly and the acceptance criterion must be "1D sixth-order + 2D max known 4--5-order".

Required fix: choose one auditable criterion. Either (a) mark U6-c as conditional and explain the 2D median degradation, or (b) split U6-c into 1D stencil verification (full pass) and 2D geometric-band diagnostic (conditional), with the parent dashboard showing all reported slopes.

### R-M2 — U8-d paper and support script still disagree on Layer C expected order

- `paper/sections/12u8_time_integration.tex:78`: U8-d table is the A/B/C viscosity-ratio test.
- `paper/sections/12u8_time_integration.tex:80`: the paper states Layer B and Layer C are both limited to slope approximately `1.0`.
- `paper/sections/12u8_time_integration.tex:94`: the reported Layer C slopes are `1.00 / 1.00`.
- `paper/sections/12u8_time_integration.tex:119`: the evaluation marks B/C first-order degradation as the expected known behavior and assigns `\triangle`.
- `experiment/ch12/exp_U8_time_integration_suite.py:20`: the support script docstring says Layer C has `O(dt^{1.5})` partial recovery.
- `experiment/ch12/exp_U8_time_integration_suite.py:229`: the implementation-level docstring repeats "expected slope 1.5" for Layer C.

Issue: the paper-level U8-d contradiction was repaired, but the cited executable evidence still advertises a different Layer C expectation. A reviewer reading or running the script cannot tell whether Layer C's `1.00` is expected degradation, failed partial recovery, or a stale comment. This keeps the U8-d PR-5 link partially non-auditable.

Required fix: align the script docstrings with the paper's current criterion (`Layer C` expected effective first order), or update both paper and data if the actual intended criterion is `O(dt^{1.5})`.

## MINOR

### R-m1 — U6 support-script console text remains stale

- `experiment/ch12/exp_U6_split_ppe_dc_hfe.py:12`: the docstring says `rho_l/rho_g >= 5` stalls for all `omega`, but the current paper text distinguishes good behavior through `rho_l <= 10` and stall for `rho_l >= 100` at `omega >= 0.5`.
- `experiment/ch12/exp_U6_split_ppe_dc_hfe.py:14`: the docstring still says split rescue is verified in `ch13 high-rho simulations`, which is not part of the current Chapter 11 support evidence.
- `experiment/ch12/exp_U6_split_ppe_dc_hfe.py:487`: the console summary says "Chapter 11 U6 table negative @ N>=64", while the current paper table reports a positive degraded slope of approximately `0.78`.
- `experiment/ch12/exp_U6_split_ppe_dc_hfe.py:492`: the console summary still prints old HFE targets `1D ~= 7.0; 2D ~= 6.33 / 5.79`, while the current paper reports `5.99 / 5.05 / 3.21`.

Issue: these are not PDF-visible, but they are reviewer-facing because Chapter 11 cites the script as the evidence source. They weaken reproducibility hygiene and can cause false objections during independent reruns.

Required fix: refresh U6 docstrings and `print_summary()` messages to exactly mirror the current table, or remove paper-specific target text from console summaries.

## Mechanical Checks

- Targeted stale-pattern grep: no hits for old `§12c/§12d/§12e` support-file refs, old nonexistent A3 paths, U7 density-ratio mismatch wording, U1 wall-boundary rationale, U9 exponential/frequency mismatch, or old summary count.
- A3 endpoint existence check: all cited `src/twophase/...` endpoints in the previous F-2 set exist.
- Syntax check: `PYTHONDONTWRITEBYTECODE=1 ... -m py_compile experiment/ch12/exp_U[1-9]_*.py` passed.
- LaTeX: `latexmk -xelatex -interaction=nonstopmode main.tex` reported all targets up-to-date.

## Required Fix Order

1. Fix U6-c acceptance semantics in the parent dashboard and detailed U6 subsection.
2. Align U8 Layer C script expectations with the repaired paper criterion.
3. Clean stale U6 script docstrings / console summaries.
4. Re-run targeted stale-pattern grep, `py_compile`, and `latexmk`.
