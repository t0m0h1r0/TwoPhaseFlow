# CHK-RA-PAPER-001 strict whole-paper review

Date: 2026-04-29
Agent: ResearchArchitect -> PaperReviewer / PaperWriter
Scope: Whole paper formatting and claim consistency, with emphasis on figures, tables, captions, headings, and cross-chapter prose.
Verdict: PASS after fixes. Pre-fix review found MAJOR consistency issues and MINOR formatting issues; all accepted issues were patched in this worktree.

## Findings and resolutions

1. MAJOR resolved -- Chapter 14 benchmark status contradicted by conclusion.
   - Evidence: `paper/sections/14_benchmarks.tex:277` now captions the summary table as "ベンチマーク受入基準と結果記入状況"; the rows still explicitly say "実験結果は計算完了次第掲載".
   - Fix: `paper/sections/15_conclusion.tex:222` now states that Chapter 14 is a YAML / diagnostics / acceptance-criteria gate, not a completed achievement; `paper/sections/15_conclusion.tex:301` and `paper/sections/15_conclusion.tex:438` explicitly say quantitative results are not yet listed.

2. MAJOR resolved -- Non-uniform CLS advection scope was overstated in the cross-V summary.
   - Evidence: V10 is fixed to `alpha=1` in `paper/sections/13e_nonuniform_ns.tex`, while V8/V9 carry the non-uniform evidence.
   - Fix: `paper/sections/13f_error_budget.tex:96` now separates Zalesak / single-vortex as uniform-grid CLS diagnostics and leaves non-uniform support to V8/V9.

3. MAJOR resolved -- HFE 2D slopes were phrased like formal convergence orders.
   - Evidence: U6-c reports effective slopes that include pre-asymptotic and round-off-floor behavior.
   - Fix: `paper/sections/15_conclusion.tex:189` and `paper/sections/15_conclusion.tex:248` now call max 11.35 / med 8.72 "effective slope" diagnostics, not formal `O(h^p)` claims.

4. MINOR resolved -- U3 GCL residual summary drifted from the source table.
   - Evidence: `paper/sections/12u3_nonuniform_spatial.tex` reports GCL `2.13e-13`.
   - Fix: `paper/sections/12_component_verification.tex`, `paper/sections/12h_summary.tex`, and `paper/sections/15_conclusion.tex:240` now use `2.13e-13`.

5. MINOR resolved -- Figure/table title punctuation was inconsistent across U/V captions.
   - Evidence: subtest captions mixed `U1-a:` / `V10:` with Japanese `U1：` style; one caption used the English-only "U9 prohibition map".
   - Fix: U/V captions now use the same full-width delimiter style; `paper/sections/12u9_dccd_pressure_prohibition.tex` now uses "U9：DCCD on pressure 禁止マップ".

## Validation

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: PASS, `paper/main.pdf` generated, 237 pages.
- Final `main.log` diagnostic grep for LaTeX warnings, package warnings, overfull/underfull boxes, missing characters, undefined control sequences, emergency/fatal errors: 0 hits.
- `git diff --check`: PASS.
- [SOLID-X] Paper/docs only; no `src/twophase/` class/module boundary changed.
