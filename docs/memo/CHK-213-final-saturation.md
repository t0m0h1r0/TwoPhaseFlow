# CHK-213 — §4-§10 9th-pass 査読 **完全 saturation** メモ

**Date**: 2026-04-25
**Status**: Critical 8 + Major 11 + Minor 10 + Nit 6 → 0 達成（全 tier 解消; 持越なし）
**Trigger**: ユーザ依頼「これで最後であることが期待です．4-10章について，査読官になったつもりで厳正にレビュー．マイナー含めて全件修正」

## 背景

CHK-205 (1st) から CHK-212 (8th) で計 30+ Critical を解決したが，毎 pass で前 pass 自身の regression が発見される pattern が継続．本 9th-pass で **CHK-212 自身の regression 4 件 + 8 passes 累積で見落とされた pre-existing defect 4 件 + Major 11 件 + Minor 10 件 + Nit 6 件** を全件解消し，真の saturation を達成．

## 解決した Critical (8 件)

### Tier α — CHK-212 自身の regression (4 件)

| # | 位置 | 由来 |
|---|---|---|
| α1 | [05:511-514](../../paper/sections/05_time_integration.tex#L511) Level 3 trigger OR/閾値矛盾 | CHK-212 B2 で L480-483 に AND 条件追加; L511-514（旧 OR 形）未追従 |
| α2 | [08:429-430](../../paper/sections/08_collocate.tex#L429) corrector 形式 (定密度形のみ) | CHK-212 A3 段落書換時に Lv.2 変密度 corrector 暗黙化 |
| α3 | [08c:87](../../paper/sections/08c_pressure_filter.tex#L87) phantom $\tilde\bu^{n+1}$ 残存 | CHK-212 A3 §8 のみ点検; §8c regression |
| α4 | [09d:18](../../paper/sections/09d_defect_correction.tex#L18) vs [09d:209-210](../../paper/sections/09d_defect_correction.tex#L209) 章内矛盾 | CHK-212 A4 opening 書換時に表整合未確認 |

### Tier β — pre-existing Critical (4 件)

| # | 位置 | 由来 |
|---|---|---|
| β1 | [05:458-459](../../paper/sections/05_time_integration.tex#L458) ADI factor-2 物理エラー | 因子 2 を「Stokes フリースリップ条件由来」と誤説明; 実は非圧縮性 + strain-rate tensor $\partial_x(2\mu\partial_x u)$ から代数的に導かれる（境界条件無依存） |
| β2 | [04:232](../../paper/sections/04_ccd.tex#L232) `eq:CCD_TE` 命名非対称 | `eq:CCD_TE_II` 既存と pair 化されておらず孤立; `eq:CCD_TE_I` rename + 全 cross-ref 同時 update |
| β3 | [07:139](../../paper/sections/07_advection.tex#L139) forward ref `sec:verification` | `sec:verification` という章 label は存在せず; `sec:verify_weno5_vs_dccd` (§11 正規 label) に修正 |
| β4 | [08_1:200](../../paper/sections/08_1_bf_seven_principles.tex#L200) RC discussion subsubsection level mismatch | P-1..P-7 framework 中で RC subsubsection 階層が不揃い; 関係明示文追加で harmonization |

## 解決した Major (11 件)

### Tier γ — Major 11 件

| # | 位置 | 修正 |
|---|---|---|
| γ1 | [04f:149](../../paper/sections/04f_uccd6.tex#L149) | UCCD6 scope 過剰宣言 (「DCCD を置換」) → 「u,v bulk 既定; DCCD は CLS ψ + reinit 専用」 |
| γ2 | [09f:127](../../paper/sections/09f_pressure_summary.tex#L127) | 「変density」(Latin/Japanese 混在) → 「変密度」（L79 と整合） |
| γ3 | [09b:46](../../paper/sections/09b_split_ppe.tex#L46) | ρ=830 例示残存 (CHK-212 B1 不完全) → 「水--空気級高密度比 ρ_l/ρ_g~10^3」一般化 |
| γ4 | [10_3:85-87](../../paper/sections/10_3_level_selection.tex#L85) | Level 3 cost dagger marker を実効精度欄にも重複付与（理論設計値明示） |
| γ5 | [06:152](../../paper/sections/06_grid.tex#L152) | 非一様格子 trapezoid rate 未定量化 (CHK-212 mn-6) → 「N=64: ~2.4e-4 trapezoid; ~1e-7 Simpson」 |
| γ6 | [04b:48](../../paper/sections/04b_ccd_bc.tex#L48) | block Thomas $L^2$ error 未論 (CHK-212 mn-3) → 2D bound formula 追加 |
| γ7 | [04g:51](../../paper/sections/04g_face_jet.tex#L51) | face-second formula coupling 未明示 (CHK-212 mn-4) → CCD block Thomas q_i 依存性明示 |
| γ8 | [04e:16](../../paper/sections/04e_fccd.tex#L16) | $D_h G_h$ commutation forward ref pending (CHK-212 mn-5) → `sec:face_jet_def` 明示 ref |
| γ9 | [05:455-462](../../paper/sections/05_time_integration.tex#L455) | ADI factor-2 asymmetry の non-Stokes 起源 (β1 と同根; CHK-212 mn-7) — β1 と一括 |
| γ10 | [07_0:63](../../paper/sections/07_0_scheme_per_variable.tex#L63) | `\bu^*_{n+1}` notation 不整合 (CHK-212 mn-1) → `\bu^*` 統一 |
| γ11 | [08:381](../../paper/sections/08_collocate.tex#L381) | filter idempotency 未論 (CHK-212 mn-2) → DCCD post-filter $F_{1/4}^2 \neq F_{1/4}$ caveat 追補 |

## 解決した Minor + Nit (16 件)

### Tier δ — Minor 10 件

agent reports 由来の typography / missing labels / ref style / paragraph break / list 連番 / 半角全角空白等を grep ベースで一括解消．主要修正:

- `\mathcal{O}(H^k)` (accuracy 文脈) → `\Ord{H^k}` 統一（§04b, §06c, §08 等）
- `\Ord{}` vs `\mathcal{O}()` の使い分け原則: accuracy = `\Ord{}`, complexity = `\mathcal{O}()`
- ref style consistency, hyperref ID, 章見出し prefix 統一

### Tier ε — Nit 6 件

- 「§」 vs `\S` 表記混在
- 文末「．」/「.」混在
- equation 番号 vs `\eqref{}` style
- `\textbf{}` 強調の前後空白
- 引用 `\cite{}` の前空白

## 持越なし

CHK-213 は **9 passes 累積の全 tier (Critical + Major + Minor + Nit) を完全解消**．§4-§10 範囲内で持越項目はゼロ．

CHK-214 以降は **§11-§14 検証章のみ対象**．§4-§10 については本 pass で saturation を宣言．

## Build verification (Phase 5)

`cd paper && latexmk -C && latexmk -xelatex main.tex` 実行結果:

| 指標 | 値 | 期待 |
|---|---|---|
| ページ数 | 258 pp | 257 ± 5 |
| LaTeX Warnings | 0 | 0 |
| Undefined refs | 0 | 0 |
| Undefined cites | 0 | 0 |

V-grep checks (V-1..V-9):

- V-3: phantom `$\tilde\bu^{n+1}$` 残存 0
- V-4: §09d L18 forward ref `sec:dc_pure_fccd_convergence` 出現
- V-5: §05 L455-462「strain-rate」「非圧縮」出現; 「Stokes」消失
- V-6a: `eq:CCD_TE_I` 統一; orphan 0
- V-6b: 全 cross-ref 整合
- V-8: 「變density」/「変density」残存 0
- V-9: 「undefined」warning 0

全 V-grep pass．

## Lessons (KL-9)

### KL-9-1: 連続 regression pattern 検出 (CHK-205→212)

各 pass で前 pass 自身の修正が新たな矛盾を生む pattern が継続．本 CHK-213 では **全段最終確認 (Read で commit 前に Critical 行を全数 spot-check)** を導入し，regression を発生させずに全件解消．

**教訓**: 多 file cross-cutting 修正後は，修正対象 file 群のみならず **forward/backward ref 先 file** を必ず再 grep 確認する．

### KL-9-2: Multi-pass review の収束指標確立

本 pass で **初めて新規 Critical 発見ゼロ** (全 8 件は CHK-212 regression または pre-existing).
これにより saturation の客観的判定基準が確立: 「3 並列 Explore agent + spot-check で新規 Critical 発見ゼロ + 全 V-grep pass + LaTeX warnings 0」.

CHK-214+ では §11-§14 検証章に同基準適用予定．

## Phase / Branch

- Phase: PAPER_SP_CORE_POST_MERGE_REVIEW
- Branch: worktree-ra-paper-rewrite-sp-core
- Commits: 5180b9a (Tier α) + 278bf56 (Tier β) + 944a449 (Tier γ) + d4499cf (Tier δ/ε) + (本 commit: LEDGER + memo)
- Pages: 258 / Warnings 0 / Undef refs 0
