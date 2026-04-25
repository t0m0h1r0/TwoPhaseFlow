# CHK-216 — §4 (CCD 章) 抜本改稿 + 純化 サマリーメモ

**Date**: 2026-04-25 / **Branch**: `worktree-ra-paper-ch4-rewrite` / **Status**: DONE

## ユーザ Trigger と要求

ユーザ指摘 (CHK-215 完了後):

1. §4 が CCD 章なのに HFE/PPE/GFM/BF の話が出てくる (§4 の自己完結性破壊)
2. FCCD/UCCD6/DCCD が説明なく冒頭 Glossary に登場 (基底 CCD 未定義のまま)
3. 「製品版 CCD」が 9 件出現するが定義文ゼロ; 対義語不明; 日英混在
4. 後章 forward ref ~60 件 (§7 移流 21 / §8 BF 19 / §9 PPE 5 / §6 非一様 6)
5. 構造・展開を一から見直す抜本改稿; 書き終えたら査読官の視点で自己レビュー

## §4 純化原則 (本改稿の最重要原則)

§4 から以下を完全排除:

| 排除対象 | 移動先 |
|---|---|
| HFE (Hermite Field Extension) | §9 PPE |
| GFM (Ghost Fluid Method) | §9 PPE |
| PPE (Pressure Poisson Equation) | §8/§9 |
| BF 7 原則 / Balanced-Force | §8 |
| 圧力勾配・表面張力 演算子整合論 | §8 |
| CSF / 曲率 / 界面遷移層 ε | §2/§7 |

§4 で許容する forward ref: 「§X 章で使用される」(用途章への用途列挙のみ; 内容詳述は禁止).

## Before / After Narrative 構造

### Before (CHK-215 完了時の §4)

```
§4 Glossary tcolorbox (L12-38)
    ├─ CCD/DCCD/FCCD/UCCD6 (基底未定義のまま列挙)
    ├─ HFE (Hermite Field Extension) ← §9 機構の予告
    ├─ GFM (Ghost Fluid Method) ← §9 機構の予告
    └─ 面ジェット
§4 tech_roadmap (L41-110)
    ├─ 中核演算子族
    └─ BF 7 原則 P-1..P-7 (§8 機構の 86 行予告)
§4.x sec:locality / sec:ccd_motivation (動機節)
§4.x 基底 CCD 導出 (sec:ccd_def, sec:ccd_omega_weights, ...)
§4.x BC (sec:ccd_bc; 04b) ← 04c より後ろに来ている
§4.x DCCD 導出形 + 製品版 spectral (04c)
    └─ §7 移流 ref 4 件 + sec:balanced_force ref 2 件 + sec:curvature ref 1 件
§4.x FCCD (04e)
    ├─ §7/§9 forward ref 4 件
    ├─ HFE Taylor 状態言及
    ├─ BF 補正 ref
    └─ 非一様格子 sketch (15 行詳述; §6 と重複)
§4.x UCCD6 (04f)
    ├─ §7 移流 ref 2 件
    └─ 高粘性比/界面帯/CLS 移流 言及
§4.x 面ジェット (04g)
    ├─ §7/§8/§10 forward ref 3 件
    ├─ HFE Taylor 状態 (eq:hfe_upwind_plus/minus)
    ├─ 変密度 PPE 整合性 (eq:face_ppe_flux)
    └─ BF 残差 ref
[章末まとめ なし]
```

問題: §4 単独で読めない; 未定義概念予告; 日英混在術語; 60+ 件の forward ref.

### After (CHK-216 完了時の §4)

```
§4.1 動機 (sec:ccd_motivation; 旧 sec:locality 統合)
    ├─ 二相流の精度要請 (5 行で簡潔)
    ├─ 3 点ステンシル + 6 次精度設計目標
    └─ 5-line chapter roadmap (CCD/DCCD/FCCD/UCCD6/面ジェット の存在理由予習)
§4.2 基底 CCD (04 + 04b)
    ├─ Chu--Fan 係数決定
    ├─ 行列構造 (sec:ccd_matrix)
    └─ 境界条件 + block Thomas (sec:ccd_bc)
§4.3 散逸的 CCD: DCCD (04c)
    ├─ 冒頭: 高波数 ξ=π Gibbs 動機 1 段落 (§4 内論理のみ)
    ├─ 導出形 spectral filter (sec:dccd_filter_theory)
    ├─ 実装デフォルト (旧「製品版」改称)
    ├─ DCCD 散逸強度設計 (sec:dccd_params; CHK-215 で §4c 集約)
    └─ §7 移流 ref 1 件 (sec:cls_advection 用途確認のみ)
§4.4 面中心 CCD: FCCD (04e)
    ├─ 冒頭: 4 設計原理 (4-1..4-4) で完結
    ├─ 4 設計原理導出
    ├─ 非一様格子 sketch 4 行に圧縮 (§6 への ref のみ)
    └─ HFE/PPE/BF 補正 言及完全削除
§4.5 風上 CCD: UCCD6 (04f)
    ├─ 冒頭: 中心差分系 Nyquist Gibbs 振動論
    ├─ Hyperviscosity (-D_2^CCD)^4 内蔵
    ├─ L^2 安定性 + CN 無条件安定
    └─ sec:time_int CN 結合 ref 1 件のみ
§4.6 出力 API: 面ジェット 𝒥_f(u) (04g)
    ├─ 冒頭: FCCD/UCCD6 出力 3 成分 API 数学的定義
    ├─ 3 成分の数値的意味 (u_f, u'_f, u''_f)
    ├─ API 設計帰結 (公開契約 / 不連続注意 / 連立局所性)
    ├─ HFE Taylor 状態 + 変密度 PPE + BF 残差 完全削除
    └─ phantomsection 5 件で §8/§9 互換維持
§4.7 章末まとめ (sec:ccd_summary; NEW)
    ├─ 数値特性比較表 (5 行 × 6 列)
    ├─ バトンパス itemize (5 用途章 へ)
    └─ 略語一覧 (CCD/DCCD/FCCD/UCCD6/面ジェット のみ; HFE/GFM 項なし)
```

成果: §4 を読むだけで完結理解可能; 用途章機構の予告ゼロ; forward ref 60→10 件.

## 9 Phase Commit 一覧

| # | Phase | Commit | 内容 | LOC |
|---|---|---|---|---|
| 0 | Worktree 作成 | (worktree add) | 新 worktree から main 分岐 | 0 |
| 1 | Phase 1 | `d4fbf58` | input 順序入替 (04 → 04b → 04c → 04e → 04f → 04g) + 04c 冒頭 1 文 | ±5 |
| 2 | Phase 2 | `05925d4` | §4 冒頭 Glossary/tech_roadmap 削除 + sec:ccd_summary skeleton | -50 |
| 3 | Phase 3 | `bcbfe2c` | §4.1 動機節書き直し + 5-line roadmap | -50 |
| 4 | Phase 4 | `8101d61` | 術語統一 (製品版/教示的 → 実装デフォルト/導出形) | ±10 |
| 5a | Phase 5a | `1fb917a` | 04c DCCD 冒頭刷新 + BF/曲率 ref 削除 | -10 |
| 5b | Phase 5b | `1a48e10` | 04e FCCD 冒頭刷新 + 非一様 sketch 4 行圧縮 | -40 |
| 5c | Phase 5c | `25bca2c` | 04f UCCD6 冒頭刷新 (Nyquist Gibbs 動機) | -15 |
| 5d | Phase 5d | `57a63dd` | 04g face-jet HFE/PPE/BF consume-side 完全削除 | -40 |
| 6 | Phase 6 | `b193592` | §4.7 章末まとめ完成 + 04e cleanup | +60 |
| 7 | Phase 7 | `d9e39ae` | 自己査読メモ + Major 4 件即時修正 | +200 |
| 8 | Phase 8 | (V-grep) | latexmk + V-1..V-8 全 pass; 256 pp clean | 0 |
| 9 | Phase 9 | (本 commit) | LEDGER + summary memo | +250 |

**総計**: 8 paper commit + 1 review memo + 1 ledger commit = 10 commit; net 約 +260 LOC (本文 -160 + memo +450).

## V-grep 検証結果 (Phase 8)

| # | 検証項目 | 期待 | 実測 |
|---|---|---|---|
| V-1 | `製品版|production 既定|教示的` in §4*/07_0* | 0 件 | 0 件 ✓ (Phase 7 で `製品` 単独 3 件も追加修正) |
| V-2 | `sec:notation_glossary|sec:tech_roadmap` | phantom + 外部 ref 解決 | ✓ |
| V-3 | `sec:fccd_nonuniform_sketch` | 04e phantom + 06c L12 ref 解決 | ✓ |
| V-4 | §4 内 `\ref{sec:advection` 件数 | ≤3 件 | 1 件 ✓ |
| V-5 | §4 内 `sec:balanced_force|sec:bf_|sec:pressure|sec:hfe|sec:gfm|sec:field_extension|sec:split_ppe` ref | 0 件 | 0 件 ✓ |
| V-6 | §4 内 `HFE|GFM|balanced[- ]force|Hermite 場|Ghost.Fluid` テキスト | 0 件 | 0 件 ✓ (phantom label 3 件は対象外; Phase 7 で `Balanced-Force` 大文字含め全件除去) |
| V-7 | `Warning.*undef|multiply.defined` in main.log | 0 | 0 ✓ |
| V-8 | ページ数 | 257 ± 5 | 256 ✓ |

## 自己査読 (Phase 7) サマリー

`docs/memo/CHK-216-ch4-rewrite-review.md` 309 行で 8 観点で抽出:

- **Critical**: 0 件
- **Major**: 0 件 (査読中に発見した 4 件は即時修正)
  - M-1: 04c L178 「製品設定」 → 「実装デフォルト設定」
  - M-2: 04c L186 「製品 DCCD」 → 「実装デフォルト DCCD」
  - M-3: 04c L193 BF H-01 残差段落 → DCCD scope 限定文に書き直し (Balanced-Force 表記排除)
  - M-4: 04c L212 「Level-2 製品」 → 「Level-2 実装既定」
- **Minor**: 5 件
  - mn-1, mn-2: §4 内で完結可能 (本 task で対処済)
  - mn-3, mn-4, mn-5: CHK-217 持ち越し (規模が §11+ 影響範囲)

## Lessons (KL-11)

- **KL-11-1**: 構造リファクタ (CHK-215) と narrative 改稿 (CHK-216) は分離 task 化すべき. 構造移動と冒頭文書き直しを混在させると review pass で焦点がぶれる. 本 task では CHK-215 の Part 構造確立が先行したことで §4 内部 narrative に集中できた.
- **KL-11-2**: Glossary 先行は読者に親切に見えて実害大. 未定義概念の先取り列挙は読解を阻害する. **章末まとめへの移動が原則**. §4 冒頭 Glossary を §4.7 章末まとめに移動した結果，読者は基底 CCD を理解した後で略語一覧を確認できるようになった.
- **KL-11-3**: Forward ref は「動機提示」と「内容誘引」を区別. 後者 (「詳細は §X」のみで内容を予告しない空虚な ref) は削除 or back-ref 化を検討. §4 純化で 60→10 件 (83% 削減) を達成.
- **KL-11-4**: 自己査読 phase を計画に組み込むことで，改稿の品質を客観的に評価できる. Critical/Major/Minor の 3 段階で deliverable を構造化すると次 task 設計に直結する. 本 task では Phase 7 査読中に Major 4 件 (V-grep miss) を発見・即時修正できた → V-grep blacklist の case-sensitive 落穴は人手 review で補完.

## CHK-217 持ち越し候補 (Minor)

1. mn-3: §11+ 検証章で UCCD6 + CN の数値検証実装 (本 task scope 外)
2. mn-4: face-jet 3 成分 API の §8 collocate / §9 ppe_solve での消費パターン明示 (§8/§9 章で実施)
3. mn-5: 非一様格子 FCCD 完全定式の §6c での narrative 整合 (§6 章 review 必要)

## 本 task で達成した目標

1. **§4 純化原則達成**: V-5 / V-6 全 pass; HFE/GFM/PPE/BF/balanced-force consume-side 機構を §4 から完全排除
2. **§4 が章単独で読める narrative 化**: 動機 → 基底 → 派生 (DCCD/FCCD/UCCD6) → 出力 API → まとめ の 7 節構造
3. **forward ref 削減**: §4 内 60→10 件 (83% 削減)
4. **術語統一**: 製品版/production 既定/教示的 → 実装デフォルト/実装既定/導出形
5. **読者導線**: §4 冒頭で 5-line chapter roadmap → 各節で動機 1 段落 (§4 内論理のみ) → §4.7 で数値特性比較表
6. **査読 deliverable**: 8 観点 309 行の客観評価; Critical 0 / Major 0 (即時修正) / Minor 5 (3 件次 task)

## Next Steps

- ユーザ確認 → main へのマージ判断 (CHK-215 と本 task の 2 worktree がある状態)
- CHK-217 候補: mn-3..mn-5 の解消 (§11+ 検証章 + §6 非一様格子整合 + §8/§9 face-jet 消費パターン)

────────────────────────────────────────────────────────

**Files modified**:
- `paper/sections/04_ccd.tex` (Glossary/tech_roadmap 削除 + §4.1 + §4.7)
- `paper/sections/04b_ccd_bc.tex` (順序前倒し)
- `paper/sections/04c_dccd_derivation.tex` (冒頭刷新 + 術語統一 + Phase 7 修正)
- `paper/sections/04e_fccd.tex` (冒頭刷新 + 非一様圧縮 + コメント修正)
- `paper/sections/04f_uccd6.tex` (冒頭刷新)
- `paper/sections/04g_face_jet.tex` (HFE/PPE/BF 完全削除 + phantom 5 件)
- `paper/sections/07_0_scheme_per_variable.tex` (術語統一)
- `paper/main.tex` (input 順序)
- `docs/memo/CHK-216-ch4-rewrite-review.md` (NEW; 査読メモ)
- `docs/memo/CHK-216-ch4-rewrite-summary.md` (NEW; 本ファイル)
- `docs/02_ACTIVE_LEDGER.md` (CHK-216 entry; CHK-215 prev_CHK 降格)
