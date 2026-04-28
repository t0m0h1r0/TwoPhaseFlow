# §12–§13 Strict Peer Review — 2026-04-28

## Verdict

**MAJOR REVISION.**

第12章と第13章は、U/V 系列の分離、2D 可視化、負の結果の明示という大枠では前回より大きく改善している。しかし現状のままでは、査読通過には不十分である。理由は、(1) §12 の互換ラベルが実ラベルを潰して参照を壊していること、(2) §13 の一部実験設定が実験スクリプトと一致しないこと、(3) V4 の失敗/条件付き結果の扱いが章頭・個別節・精度バジェットで矛盾していること、の3点が科学的再現性と読者信頼性を直接損なうためである。

Severity count: **0 Fatal / 10 Major / 6 Minor**.

## Fix Summary

Post-remediation verdict: **PASS**.

All findings in this review were addressed in commit `85072b9`.

- M1: Removed the stale backward-compat `sec:verify_summary` / `tab:verification_summary` labels from the chapter parent and connected `12h_summary.tex`; labels now resolve to §12.8 and the real summary table.
- M2: Aligned V8/V9 paper settings with the active experiments (`rho_l/rho_g=10`, `We=10`, `r=0.25`, `sigma=1`, `dt=0.20 h_min`).
- M3--M5: Reframed V4 as fixed-wall Galilean offset residual plus RT growth-rate miss; V4-a is conditional, V4-b is a failed linear-growth validation / preliminary diagnostic, and §13f no longer contradicts the V4 error-source analysis.
- M6: Removed the undefined `HHO-PPE` term and described the V1 pressure step as PPE projection.
- M7: Unified §12 verdict taxonomy for U1-c, U6-b, and U8-d across parent table, detailed sections, and final summary.
- M8--M10: Replaced the stale “19 benchmarks” count, made V10 time-step definition reproducible, and rewrote V5 CCD/FD suppression as parameter-dependent rather than a flat 3--6x claim.
- m1--m6: Unified static-droplet terminology to `静止液滴`, normalized visible punctuation/English filler, weakened finite-experiment “proof” language, removed the unsupported V3 peak-convergence aside, corrected the V6 spread statement, and removed script/data path comments from §12--§13 sources.

Validation after fixes:

- `git diff --check` passed.
- `cd paper && latexmk -g -xelatex -interaction=nonstopmode main.tex` succeeded, 224 pages.
- Log scan found 0 undefined references, 0 undefined citations, 0 multiply-defined labels, and 0 rerun warnings.
- Review-residue scan for `HHO`, `19 件`, `h_{\min}/0.5`, `静的液滴`, `証明`, `補間誤差支配`, script/data comments, `smoke`, `synthesis`, and related stale terms returned no hits in §12--§13 scope.

## Scope

- Reviewed source:
  - `paper/sections/12_component_verification.tex`
  - `paper/sections/12h_summary.tex`
  - `paper/sections/12u*.tex`
  - `paper/sections/13_verification.tex`
  - `paper/sections/13a_single_phase_ns.tex`
  - `paper/sections/13b_twophase_static.tex`
  - `paper/sections/13c_galilean_rt.tex`
  - `paper/sections/13d_density_ratio.tex`
  - `paper/sections/13e_nonuniform_ns.tex`
  - `paper/sections/13f_error_budget.tex`
- Spot-checked experiment settings where the paper’s reproducibility claims depended on script constants:
  - `experiment/ch13/exp_V8_nonuniform_ns_static.py`
  - `experiment/ch13/exp_V9_local_eps_nonuniform.py`
  - `experiment/ch13/exp_V10_cls_advection_nonuniform.py`

## Strengths

- U 系列と V 系列の章分離は概ね成功している。第12章は component verification、第13章は integrated solver verification として読める。
- V7, V9, V10-b のような負または条件付き結果を隠していない点は良い。
- V3/V10 の 2D 可視化追加により、表だけでは分からない形状・場の診断が改善している。
- §13f の横断的な精度バジェットは、章全体の読者導線として有用である。

## Major Findings

### M1 — §12 の互換ラベルが実ラベルを潰し、参照が壊れている

Evidence:
- `paper/sections/12_component_verification.tex:32` defines `\label{sec:verify_summary}`.
- `paper/sections/12_component_verification.tex:38` defines `\label{tab:verification_summary}`.
- `paper/sections/12h_summary.tex:7` defines the real `\label{sec:verify_summary}`.
- `paper/sections/12h_summary.tex:21` defines the real `\label{tab:verification_summary}`.
- `paper/main.aux` currently resolves both labels to Chapter 12 / page 123 rather than the summary subsection/table.

Impact:
- `表~\ref{tab:verification_summary}` can resolve to the chapter counter, not the table counter.
- This is especially damaging because §12 summary is the chapter’s evidentiary backbone.

Required fix:
- Remove these two backward-compat labels from `12_component_verification.tex`, or rename them to explicit legacy labels that are never used for current table/subsection references.
- Rebuild with a forced LaTeX run and scan for duplicate labels.

### M2 — V8/V9 の紙面設定がスクリプト設定と一致していない

Evidence:
- `paper/sections/13e_nonuniform_ns.tex:21` states V8 uses `\rho_l=\rho_g=1`.
- `experiment/ch13/exp_V8_nonuniform_ns_static.py:64-67` uses `RHO_L = 10.0`, `RHO_G = 1.0`.
- `paper/sections/13e_nonuniform_ns.tex:23` states `\Delta t = h_{\min}/0.5`.
- `experiment/ch13/exp_V8_nonuniform_ns_static.py:68,118` uses `CFL_FACTOR = 0.20`, `dt = CFL_FACTOR * h_min`.
- `paper/sections/13e_nonuniform_ns.tex:75` states V9 uses `r=0.0625, \sigma=0.025`.
- `experiment/ch13/exp_V9_local_eps_nonuniform.py:64-70` uses `R = 0.25`, `SIGMA = 1.0`, `WE = 10.0`, `RHO_L = 10.0`, `RHO_G = 1.0`.
- `paper/sections/13e_nonuniform_ns.tex:80` again states `\Delta t = h_{\min}/0.5`, while the script uses `dt = 0.20 h_min`.

Impact:
- V8/V9 are not reproducible from the paper.
- V8/V9 conclusions about non-uniform grid stability and local epsilon are tied to density ratio, time step, and capillary scaling; these are not cosmetic parameters.

Required fix:
- Make the paper match the executed settings, or regenerate data for the paper settings.
- Include `\rho_l/\rho_g=10`, `\Delta p_{\mathrm{exact}}=\sigma/(R\,We)=0.4` if that is the intended reduced-We formulation.
- Replace `h_{\min}/0.5` with the actual CFL expression.

### M3 — V4 の判定が章頭・個別節・精度バジェットで一貫していない

Evidence:
- `paper/sections/13_verification.tex:24-27` categorizes V1/V2/V3/V5/V6/V8/V10-c as supporting, V7/V9 as unmet, and V10-b as conditional; V4 is absent.
- `paper/sections/13c_galilean_rt.tex:54` calls V4-a conditional pass.
- `paper/sections/13c_galilean_rt.tex:121-124` says V4-b should be `\times` as a linear growth-rate verification, but then records it as `\triangle`.
- `paper/sections/13f_error_budget.tex:66-68` lists V4-a/V4-b as conditional.

Impact:
- A reader cannot tell whether V4 supports, weakens, or lies outside the paper’s claims.
- This is exactly the kind of inconsistency reviewers interpret as selective framing.

Required fix:
- Add V4 to the §13 opening verdict policy.
- Split V4-a and V4-b explicitly:
  - V4-a: not a true Galilean invariance proof; wall/gauge residual diagnostic only.
  - V4-b: not an accepted linear growth-rate validation; at best a smoke/setting diagnostic, or mark `\times`.

### M4 — V4-a は「Galilean 不変性」の検証として過大主張されている

Evidence:
- `paper/sections/13c_galilean_rt.tex:29-30` reports `\|\Delta u\|_\infty^{end}=2.07e-1` for `\|\bm U\|=0.1`.
- `paper/sections/13c_galilean_rt.tex:25-26` admits the test is not a strict periodic Galilean invariance test.
- `paper/sections/13c_galilean_rt.tex:57-59` explicitly says the result does not exclude solver-level Galilean invariance violation and that full validation requires ALE.

Impact:
- The subsection title and table summary promise a property that the experiment cannot verify.
- A reviewer will reject “conditional pass” as too generous unless the title and claim are demoted.

Required fix:
- Rename V4-a to something like “固定壁・参照点ゲージ下の Galilean offset residual”.
- In §13 summary, avoid calling it “Galilean 不変性” without a qualifier.

### M5 — §13f が V4-a の誤差源について V4 本文と矛盾している

Evidence:
- `paper/sections/13c_galilean_rt.tex:32-35` says interpolation error is about `6e-8` and cannot explain the observed `0.2` difference.
- `paper/sections/13f_error_budget.tex:35` summarizes V4-a as `$0.21$ (補間誤差支配)`.

Impact:
- This is a direct internal contradiction.
- It makes the master accuracy summary unreliable.

Required fix:
- Replace “補間誤差支配” with “壁境界・参照点ゲージ・初期サンプリング支配” or a shorter equivalent.

### M6 — V1 に未定義の `HHO-PPE` が混入している

Evidence:
- `paper/sections/13a_single_phase_ns.tex:19` uses `\textsc{HHO}-PPE`.
- Targeted scan found no other `HHO` definition in the paper sections.

Impact:
- HHO is a known numerical-method acronym outside this paper, so this reads as a stray method claim rather than a typo.
- It confuses the pressure-solve stack used in V1.

Required fix:
- Replace with the actual pressure projection used by the paper, likely CCD-PPE / PPE projection / one-field PPE, depending on the intended V1 stack.

### M7 — §12 の成績表・総括表・個別節で判定が揺れている

Evidence:
- `paper/sections/12_component_verification.tex:101` lists U1-c design as `6`, measured `4.00 / 4.00`, verdict `\triangle`.
- `paper/sections/12h_summary.tex:32` instead states U1-c expected accuracy is “評価配置上 `O(h^4)`”.
- `paper/sections/12_component_verification.tex:113` marks U6-b as `\triangle`.
- `paper/sections/12h_summary.tex:54` marks the same high-density lumped-PPE limit as `\checkmark`.
- `paper/sections/12u6_split_ppe_dc_hfe.tex:109-113` calls the high-density slope `0.78` a structural limitation but ends with `\checkmark（限界明示）`.
- `paper/sections/12_component_verification.tex:120` marks U8-d as `\triangle`.
- `paper/sections/12h_summary.tex:63` marks U8-d as `\checkmark†`.
- `paper/sections/12u8_time_integration.tex:119-121` marks U8-d as `\triangle`.

Impact:
- The reader cannot infer a stable verdict taxonomy.
- “Known degradation” is sometimes `\triangle` and sometimes `\checkmark`, which weakens the negative-result discipline established in §13.

Required fix:
- Define a single rule:
  - `\checkmark`: design claim met.
  - `\triangle`: known degradation / conditional metric / limitation quantified.
  - `\bullet`: negation test succeeds.
- Apply it consistently across `tab:U_summary`, `tab:verification_summary`, and each U section.

### M8 — §12 says §13 contains 19 integrated benchmarks, but §13 presents V1--V10

Evidence:
- `paper/sections/12h_summary.tex:128-129` says the next chapter performs “19 件の統合ベンチマーク”.
- `paper/sections/13_verification.tex:15-16` says §13 evaluates “10 個の独立した統合検証実験 V1--V10”.

Impact:
- This looks like a stale count from an earlier organization.
- If “19” counts subcases, that count must be explained and mapped.

Required fix:
- Change “19 件” to “V1--V10” or explicitly define the 19 sub-benchmarks in a table.

### M9 — V10 の時間刻み設定が再現可能な形で書かれていない

Evidence:
- `paper/sections/13e_nonuniform_ns.tex:140` states `\Delta t = h_{\min} \cdot \mathrm{CFL}_{\max}`.
- `experiment/ch13/exp_V10_cls_advection_nonuniform.py:149-151` computes `dt_est = 0.25 * h_min / max(u_max, 1e-3)`, then adjusts `dt = T_REV / n_steps`.
- `experiment/ch13/exp_V10_cls_advection_nonuniform.py:212-214` uses the same velocity-normalized/final-time-adjusted rule for single vortex.

Impact:
- The paper omits the velocity scale and final-time adjustment.
- For Zalesak rigid rotation, `u_max` is not 1, so the current expression is dimensionally and numerically misleading.

Required fix:
- State `\Delta t \approx 0.25 h_{\min}/\max|\bm u|`, with final-step adjustment to close exactly at one period/reversal time if that is part of the experiment definition.

### M10 — V5 の「CCD は FD 比 3--6 倍抑制」はデータ全体の代表として不正確

Evidence:
- `paper/sections/13f_error_budget.tex:83` says “CCD 演算子は FD 比 `3`--`6` 倍抑制”.
- `paper/sections/13b_twophase_static.tex:107-109` contains cases ranging from near parity at `\rho_r=100,N=128` to much stronger suppression at coarse/high-contrast cases.
- `paper/sections/13b_twophase_static.tex:125-126` cites two selected ratios: `1/5.9` and `1/2.5`.

Impact:
- The summary hides strong parameter dependence.
- A reviewer will ask whether the “3--6” range is a median, selected subset, or stale abstract number.

Required fix:
- Replace with parameterized wording: “CCD は全表ケースで FD 以下；代表的には `N=32,\rho_r=1` で `1/5.9`、`\rho_r=100,N=64` で `1/2.5`、高解像度・高密度比では差が縮小”.

## Minor Findings

### m1 — `静的液滴` と `静止液滴` が混在している

Evidence:
- `paper/sections/12_component_verification.tex:77` uses `静止液滴`.
- `paper/sections/13_verification.tex:12`, `paper/sections/13b_twophase_static.tex:12`, and `paper/sections/13e_nonuniform_ns.tex:12` use `静的液滴`.

Recommendation:
- Prefer one term. For CFD benchmark prose, `静止液滴` is more natural and already used in §12.

### m2 — 日本語句点と英語表現の体裁が一部崩れている

Evidence:
- `paper/sections/13c_galilean_rt.tex:59`, `113`, `118`, `154` include Japanese `。` while most chapters use `．`.
- `paper/sections/13f_error_budget.tex:9`, `106` use “synthesis” in visible headings/prose.
- `paper/sections/13e_nonuniform_ns.tex:117` uses “safe default”.

Recommendation:
- Normalize to the §1--§3 style: Japanese prose with `．`, and English terms only when notation or standard benchmark names require them.

### m3 — “証明” が有限実験に対して強すぎる

Evidence:
- `paper/sections/13b_twophase_static.tex:131` says “時間頑健性証明”.
- `paper/sections/13d_density_ratio.tex:37` says “定量証明”.
- `paper/sections/12u9_dccd_pressure_prohibition.tex:15` says “逆に証明する”.

Recommendation:
- Replace with “確認”, “示す”, “裏付ける”, or “否定検証する”.

### m4 — V3 caption contains an unsupported “separately confirmed” claim

Evidence:
- `paper/sections/13b_twophase_static.tex:55-56` says V5 separately confirms peak convergence in the `h -> 0` limit.
- V5 uses final-time values, not peak-over-history values.

Recommendation:
- Either include the actual peak-convergence evidence or weaken the sentence to “final-time 指標で切り分ける”.

### m5 — V6 caption’s cross-density spread claim is slightly too sharp

Evidence:
- `paper/sections/13d_density_ratio.tex:35-36` says cross-density `|\Delta p_rel|` stays within `<=0.06%` except `rho_r=833,N=32`.
- For `N=32` and `rho_r=2,10,100`, the spread is about `0.076%` (`0.422%` vs `0.346%`).

Recommendation:
- Use `\lesssim 0.08%` or restrict the `0.06%` statement to `N>=64`.

### m6 — Source comments still contain script/result paths

Evidence:
- Several §12/§13 files include source comments such as `Script`, `Scripts`, `Data`, and `results/...`.

Recommendation:
- This is not visible in the PDF, so it is not a reader-facing defect. If source distribution is part of the deliverable, remove or standardize these comments to avoid contradicting the “paper prose should not expose implementation paths” policy.

## Required Remediation Order

1. **Fix label collisions first.** This is the easiest high-impact correction and prevents false confidence from LaTeX “successful” builds.
2. **Align V8/V9/V10 settings with the scripts or regenerate the experiments.** Reproducibility must be restored before prose polishing.
3. **Rewrite V4 framing.** Demote V4-a to a residual diagnostic and mark V4-b consistently as either `\times` or strictly conditional smoke, not both.
4. **Normalize §12 verdict taxonomy.** U1-c/U6-b/U8-d must have identical verdicts in parent table, detailed subsection, and final summary.
5. **Clean terminology and overclaim wording.** Remove `HHO`, “証明”, stale counts, and visible English filler.

## Suggested Validation After Fixes

- `rg -n '\\label\\{(sec:verify_summary|tab:verification_summary)\\}' paper/sections/12*.tex`
- `rg -n 'HHO|補間誤差支配|19 件|h_\\{min\\}/0\\.5|静的液滴|。|証明' paper/sections/12*.tex paper/sections/13*.tex`
- `git diff --check`
- `cd paper && latexmk -g -xelatex -interaction=nonstopmode main.tex`
- Log scan for undefined references, multiply-defined labels, and rerun warnings.
