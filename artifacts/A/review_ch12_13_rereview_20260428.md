# §12–§13 Strict Re-Review — 2026-04-28

## Verdict

**ACCEPT WITH MINOR EDITS.**

前回の Major 指摘はすべて解消されている。§12 の重複ラベル問題は修正され、`sec:verify_summary` は §12.8、`tab:verification_summary` は Table 34 に解決する。V8/V9/V10 の設定は実験スクリプト由来の値へ戻され、V4 は「厳密な Galilean 不変性検証」ではなく固定壁・参照点ゲージ下の offset 残差診断として再定義された。V4-b/V7/V9 の負の結果も章頭と精度バジェットで一貫している。

Severity count: **0 Fatal / 0 Major / 2 Minor / 1 Nit**.

## Checks Performed

- Previous-review residue scan:
  - `HHO`, `19 件`, `h_{\min}/0.5`, `静的液滴`, `証明`, `補間誤差支配`, script/data comments, `smoke`, `synthesis`, stale V10 wording: no hits in §12--§13 scope.
- Duplicate-label scan:
  - no duplicate labels in `paper/sections/12*.tex` and `paper/sections/13*.tex`.
- LaTeX:
  - `cd paper && latexmk -g -xelatex -interaction=nonstopmode main.tex` succeeded, 224 pages.
  - log scan found 0 undefined references, 0 undefined citations, 0 multiply-defined labels, and 0 rerun warnings.
- Label resolution:
  - `sec:verify_summary` → §12.8, page 137.
  - `tab:verification_summary` → Table 34, page 138.

## Resolved Major Items

- **Label integrity:** previous §12 summary/table label collision is closed.
- **Experiment reproducibility:** V8/V9 state `rho_l/rho_g=10`, `We=10`, `r=0.25`, `sigma=1`, and `dt=0.20 h_min`; V10 states velocity-normalized final-time-adjusted time stepping.
- **V4 framing:** V4-a is now a conditional Galilean offset residual diagnostic, and V4-b is a failed linear-growth validation / preliminary diagnostic.
- **Undefined method term:** `HHO-PPE` has been removed.
- **§12 verdict taxonomy:** U1-c, U6-b, U8-d are consistently conditional across parent and summary tables.
- **Stale counts and overcompressed claims:** the stale “19 benchmarks” count is gone; the main V5 design guidance is parameterized rather than flat 3--6x.

## Remaining Minor Findings

### m1 — §12 summary still calls the V4 connection “Galilean 不変性＋RT”

Evidence:
- `paper/sections/12h_summary.tex:135` says `界面--圧力相互作用 → Galilean 不変性＋RT 不安定性`.

Impact:
- This is not scientifically fatal because §13 itself correctly frames V4 as an offset residual diagnostic.
- However, it reintroduces the old promise at the §12→§13 transition.

Recommended fix:
- Replace with `Galilean offset 残差＋RT 不安定性`.

### m2 — §13f still summarizes V5 as a fixed `1/3--1/6` suppression range in one place

Evidence:
- `paper/sections/13f_error_budget.tex:55` says `CCD/FD 比 $1/3$--$1/6$ 抑制`.
- The later design-guidance paragraph correctly states the parameter dependence and representative ratios at `paper/sections/13f_error_budget.tex:82-84`.

Impact:
- This is weaker than the previous Major issue because the final design-guidance paragraph is now correct.
- Still, the error-source stack can be read as a global range.

Recommended fix:
- Replace the line with parameterized wording, e.g. `V5 では全表ケースで CCD が FD 以下であり，粗格子・低密度比ほど抑制が大きい`.

## Nit

### n1 — V9 setting bullets use ASCII periods

Evidence:
- `paper/sections/13e_nonuniform_ns.tex:77-79` end the A/B/C setting lines with `.`.

Impact:
- Cosmetic only.

Recommended fix:
- Replace with Japanese `．` for §1--§3 style consistency.

## Final Assessment

The manuscript no longer has a reviewer-blocking defect in Chapters 12--13. The remaining items are small editorial consistency issues. If the next task is “対応”, they can be fixed in one surgical patch without rerunning experiments.

