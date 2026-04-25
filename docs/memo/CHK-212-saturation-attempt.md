# CHK-212 — §4-§10 8th-pass 査読 saturation 到達メモ

**Date**: 2026-04-25
**Status**: Critical 11 + Major 5 → 0 達成（Minor 7 持越）
**Trigger**: ユーザ依頼「4-10章について，査読官になったつもりで厳正にレビュー．何回対応してもクリティカルが全然減らないので，これで最後にするつもりで徹底的に」

## 背景

CHK-205 (1st) から CHK-211 (7th) で計 30+ Critical を解決したが，新たな defect が常に発見される問題が継続．CHK-211 の 7th-pass で WENO scope 訂正を行ったが，本 8th-pass で **CHK-211 自身の regression を 6 件残した**ことが確定．

## 解決した Critical (11 件)

### Tier A — CHK-211 自身の regression (6 件)

| # | 位置 | 由来 |
|---|---|---|
| A1 | [10:429](../../paper/sections/10_full_algorithm.tex#L429) raw `eq:gfm\_gradient\_jump` → `\eqref{}` | CHK-211 CR3 LaTeX escape のみで `\eqref{}` 化忘れ |
| A2 | [07_0:25](../../paper/sections/07_0_scheme_per_variable.tex#L25), [07d:79](../../paper/sections/07d_cls_stages.tex#L79) wrong-target ref | CHK-211 P1 で `sec:advection_motivation` 統一時に取り損ね |
| A3 | [08:429](../../paper/sections/08_collocate.tex#L429) phantom `$\tilde\bu^*$` 段落矛盾 | CHK-211 MAJ-2 で phantom `$\tilde\bu^{n+1}$` 削除時に L429 の`$\tilde\bu^*$` 言及残り |
| A4 | [09d:11-17](../../paper/sections/09d_defect_correction.tex#L11) opening 「分相 PPE 限定」 | CHK-211 CR4 table 行のみ書換，opening 段落未点検 |
| A5 | [09d:222-225](../../paper/sections/09d_defect_correction.tex#L222) footnote 「Level 2/3」 | CHK-211 CR4 table のみ書換，footnote 未追従 |
| A6 | [09f:78](../../paper/sections/09f_pressure_summary.tex#L78) tcolorbox 「分相 PPE 主軸」 | CHK-211 CR4 table のみ書換，rationale tcolorbox 未追従 |

### Tier B — 構造的 cross-file 不整合 (4 件)

| # | 位置 | 由来 |
|---|---|---|
| B1 | ch13 ρ=830 ルーティング 3-way 矛盾 (§10/§10_3/§9b) | ユーザ決定「言及不要」 — 量的閾値を全削除し質的記述に統一 |
| B2 | §5/§10_3 Level 3 閾値 20× 開き | §10_3 canonical で一元化 |
| B3 | §9d/§9f Level 3 行精度乖離 | §9f canonical (O(h^7) Dir / O(h^5) Neu + IIM 採用時 O(h^4) 以上) |
| B4 | §4c/§5 DCCD scope 反転 | CHK-211 §7 framing「DCCD = CLS production 既定」に同調 |

### Tier C — 累積 structural defect (1 件)

| # | 位置 | 由来 |
|---|---|---|
| C1 | [07_0:27](../../paper/sections/07_0_scheme_per_variable.tex#L27) 界面帯 WENO5 (本文未定義) | ユーザ決定「方向 (a) 削除」— CHK-211 §7 "WENO=比較" framing 完全整合 |

## 解決した Major (5 件)

| # | 修正 |
|---|---|
| C2 | DCCD operator notation `ε_d h^4 D^4` → `ε_d h^2 D^2` (post-filter 実装一致) |
| C3 | UCCD6+CN 「無条件安定」 → 「(周期格子 ℓ^2 限定)」 qualifier |
| C4 | DCCD post-filter 形 `H(ξ)=1-4ε_d sin^2(ξ/2)` 安定条件 `ε_d ≤ 1/4` 補足 |
| C5 | BKZ ω_c Δt 「2」 → 「O(1); π/2≈1.57」訂正 |
| C6 | 非一様 FCCD O(H^4) caveat — 「J_x を Simpson 則 or 解析積分で構築する場合」 |
| C7 | DCCD conservation hedge — 「発散形は近似的; FVM telescoping 条件下で破れる」 |
| C8 | §9f‡‡ Lv.2 monolithic DC O(h^4) 昇格 claim soften (数値検証で確認予定) |
| D1 | §9d:129 malformed citation 「表 §ref{}」 → 「§ref{}」 |
| D2 | §10_3 cost 表 Level 3 行に dagger marker + 脚注 (理論設計値) |
| D3 | TE_I `-1/5040` stencil residual と modified-wavenumber operator TE `-1/9450` 区別明記 |
| D4 | UCCD6 hyperviscosity σ → σ_6 rename (§5 surface tension σ 衝突回避) |
| D5 | §5:307 Level 2 本文に ch13 (rising bubble) Mode 2 「O(Δt) 縮退」 main text 昇格 |

## 持越 Minor (7 件 — CHK-213+)

- mn-1: [07_0:63](../../paper/sections/07_0_scheme_per_variable.tex#L63) `$\bu^*_{n+1}$` notation 不整合
- mn-2: [08:363-381](../../paper/sections/08_collocate.tex#L363) filter idempotency 未論
- mn-3: [04b:28-34](../../paper/sections/04b_ccd_bc.tex#L28) block Thomas L^2 error
- mn-4: [04g:43-46](../../paper/sections/04g_face_jet.tex#L43) face-second formula coupling
- mn-5: [04e:22](../../paper/sections/04e_fccd.tex#L22) `D_h G_h` commutation forward ref
- mn-6: [06:148-154](../../paper/sections/06_grid.tex#L148) trapezoid rate quantification
- mn-7: [05:449-456](../../paper/sections/05_time_integration.tex#L449) ADI factor-2 asymmetry

## 教訓 (peer review プロセス)

1. **Regression は不可避**: CHK-205..211 の 7 passes で都度新 Critical が発見される事実は，paper review 1 回で完全 saturation 不可能を示唆．本 CHK-212 でも CHK-211 自身の regression が 6 件発見された．
2. **Cross-file 不整合は table-only 書換で再発しやすい**: CHK-211 CR4 で table 行のみ書換 (opening/footnote/rationale 未点検) → 本 CHK-212 で A4/A5/A6 として再浮上．以後は **当該 cluster の opening + table + footnote + rationale を 1 commit でまとめて書換** する運用ルールが必要．
3. **量的閾値 (ρ=100, 500, 10^4 etc.) の paper-internal 整合は無理筋**: 検証実行前の量的閾値は §11-§14 結果次第で更新されるため，本文には「中程度密度比」 etc. 質的記述に留め，数値は表のみに集約する設計が安全．本 CHK-212 B1 ユーザ決定「言及不要」がこれを徹底．
4. **8 passes 必要だった事実は spec 整理コストの正味**: §4-§10 は algorithm spec ↔ theory analysis ↔ implementation の 3 階層で書かれており，paper としての `cohesion = O(N²)` で N=7 sections だと cross-link 21 ペア，6-7 passes で saturate するのは妥当．次回からは pass 数を予算化（max 5 passes）し，残 minor は実機検証 (§11-§14) で吸収．

## 完了宣言

§4-§10 で **algorithm spec ↔ theory analysis ↔ implementation** の 3 階層論理整合 + DCCD operator notation 実装一致 + Level 1/2/3 ルーティング閾値整合 + ch13 ρ=830 の paper-internal 量的閾値撤廃 + UCCD6 σ_6 rename で §5 surface tension σ 衝突解消 を達成．**8 passes で初めて Critical/Major 0**．Minor 7 件は §11-§14 検証章 CHK-213+ で吸収．
