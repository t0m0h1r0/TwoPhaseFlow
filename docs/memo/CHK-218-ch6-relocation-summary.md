# CHK-218 — §6（界面適合非一様格子）を Part 2 末尾へ移動 + 前方参照整合

**Date**: 2026-04-26
**Branch**: `worktree-ra-paper-ch4-rewrite`
**Phase**: PAPER_CH6_RELOC
**Trigger (User)**:
> 「6 章非一様格子はパート 2 の最後の章が良い．一様格子で学んだのち，非一様へ拡張という形の方が理解しやすい．移動して．各章で非一様格子拡張への言及があるなら，この移動にあわせてその記述も移動すべき．」

**狙い**: §4-§5-§7-§8-§9 を「一様格子上の数値アルゴリズム」として一気通貫で読ませ，
最後に §6（旧 §6 = 界面適合非一様格子）で非一様拡張を一括導入する pedagogical flow．
§6 を Part 2 末尾の「拡張章」として位置付け，読者の認知負荷を低減．

---

## 構造変更 before / after

### before（CHK-217 完了時点）

```
Part 2 数値アルゴリズム
├─ §4  CCD 演算子
├─ §5  時間積分
├─ §6  界面適合非一様格子      ← 中央配置（読者が一様→非一様の移行で混乱）
├─ §7  移流項
├─ §8  圧力連成（Collocate）
└─ §9  PPE
```

### after（CHK-218 完了時点）

```
Part 2 数値アルゴリズム
├─ §4  CCD 演算子
├─ §5  時間積分
├─ §6  移流項                  ← 旧 §7
├─ §7  圧力連成（Collocate）   ← 旧 §8
├─ §8  PPE                     ← 旧 §9
└─ §9  界面適合非一様格子      ← 旧 §6（末尾配置 = 拡張章として一括導入）
```

ラベル `\ref{}` は LaTeX が自動解決するため章番号 textual hardcode のみ手動更新．

---

## Phase 別 commit / 影響 LOC

| # | Phase | Commit | 内容 | LOC |
|---|---|---|---|---|
| 1 | Phase 1 | `46ad1ae` | `paper/main.tex` の §6 input ブロック (06_grid + 06b/06c/06d) を §5 直後 → §9f_pressure_summary 直後へ移動 | ±10 |
| 2 | Phase 2 | `7cf0dd0` | 純粋予告段落 DELETE — 04_ccd L103-107 (5 行) / 04e L161-169 (subsubsection 9 行 + 2 phantomsection labels) / 03d L226-243 (subsubsection 17 行 + 1 label) + 06d_ridge_eikonal_nonuniform 本文を D1--D4 新規導入形に書換 + ラベル参照修正 (10_5 / 04e / 06c / 06d) | -38 / +18 |
| 3 | Phase 3 | `edae99c` | 章間 transition REWRITE — 05 L655-656「次章では…非一様格子上で…座標変換理論」 → 「次章では…CLS/運動量/粘性の用途別配分」 + 08 L6「§sec:grid_gen で構築した界面適合非一様格子上に」 → 「界面適合非一様格子（§sec:grid 章で詳述）上に」 (forward-ref 時制 framing 整合) | ±5 |
| 4 | Phase 4 | `69f32f3` | tab:chapter_overview 行入替 + textual 章番号更新 — 01b L150-203 表で旧 §6 grid 行を最後尾の新 §9 grid 行へ移動 + 前提章列再計算; 旧 §7-§9 行を新 §6-§8 にシフト + 前提章再計算; 01b L216 「第 4 章・第 6 章・第 8--9 章」 → 「第 4 章・第 6--9 章」; 07_advection L21-23 textual「(§7.3)」/「(§8.4)」/「(§7.6)」 → 「(§6.3)」/「(§7.4)」/「(§6.6)」 | ±15 |
| 5 | Phase 5 | `94611f1` | % comment self-doc 一斉更新 — 19 ファイル (04c / 04g / 07_advection / 07_0 / 07b / 07c / 07d / 07e / 08_collocate / 08_0 / 08_1 / 08_2 / 08b / 08c / 09_ccd_poisson + filename typo 修正 / 09b / 09c / 09d / 09f) のヘッダ / 本文中 `% §X.Y` 表記を新章番号体系に同期; body 出力非影響だが grep 時の誤誘導回避 | ±32 |
| ★ | Phase 2 spillover | `e2fae70` | 03d L257 章末「本節の要点」リスト 1 行 bullet「非一様格子への拡張は D1--D4 の補正で完結する」削除 — D1--D4 定義は §9 (06d) に集約され forward-ref として誤誘導するため | -1 |
| 6 | Phase 6 | (no commit) | latexmk -xelatex main.tex clean build verify | 0 |
| 7 | Phase 7 | (this commit) | LEDGER + summary memo | +memo |

**総計**: 6 paper commit + 1 ledger; net 本文 ≒ -30 LOC; build 256 pp．

---

## V-grep 検証結果

| # | 検証項目 | 期待 | 実測 | 結果 |
|---|---|---|---|---|
| V-1 | main.tex input 順序 | 04 → 04* → 05 → 07_0/07/07c/07b/07d/07e → 08*/08_0/08_1/08_2/08b/08c → 09/09b/09c/09d/09e/09f → 06/06b/06c/06d → 10 | 一致 | ✅ |
| V-2 | `grep -n "sec:fccd_nonuniform_sketch\|eq:fccd_nonuniform_coeffs" sections/*.tex` | 0 件 | 0 件 | ✅ |
| V-3 | `grep -nE "非一様格子への拡張" sections/03d*.tex sections/04*.tex` | 0 件 | 0 件 (Phase 2 spillover で L257 bullet も除去後) | ✅ |
| V-4 | `grep -n "で構築した界面適合非一様格子" sections/08_collocate.tex` | 0 件 | 0 件 | ✅ |
| V-5a | undef refs | 0 | 0 | ✅ |
| V-5b | multiply defined | 0 | 0 | ✅ |
| V-7 | page count | 257 ± 5 | 256 | ✅ |

---

## 削除対象の論理 / KEEP との切り分け

CHK-218 で適用した「forward-ref severity 3 階層」分類:

| 階層 | 例 | 処理 |
|---|---|---|
| (a) 純粋予告段落 | 04_ccd L103-107「本章では一様格子…第~\ref{sec:grid}章で体系的に整備する」 / 04e L161-169 subsubsection「非一様格子への拡張（予告）」 / 03d L226-243 subsubsection「D1--D4」 / 03d L257 章末 bullet | **DELETE**（§6 が後続章として後で出現するため予告は不要） |
| (b) 章間 transition | 05 L655-656「次章では…」/ 08 L6「§sec:grid_gen で構築した…上に」 | **REWRITE**（次章対象が §7 移流に変わるため transition 文を新章順序に整合） |
| (c) scheme 統合 context | 07_advection L38- subsection「非一様格子上の CLS 演算」/ 07b L131-148「非一様格子への拡張」段落 / 09b L72-77 / 09d L138 等 | **KEEP**（scheme 固有の非一様変種議論で §7-§9 文脈に統合; §6 へ移すと duplicate context が必要となり narrative 破綻） |

---

## ラベル変更 mapping

| 旧ラベル / ファイル | 処理 | 新ラベル / 参照先 |
|---|---|---|
| `sec:fccd_nonuniform_sketch` (04e L165) | **削除** | `sec:fccd_nonuniform` (06c) で代替 |
| `eq:fccd_nonuniform_coeffs` (04e phantomsection) | **削除** | 04e L206 参照を `sec:fccd_nonuniform` に書換 |
| `sec:ridge_eikonal_nonuniform` (03d L240) | **削除** | `sec:ridge_eikonal_nu_grid` (06d) で代替; 10_5 L76 参照修正 |
| 06d 本文の 03d sketch 参照 | **書換** | D1--D4 を 06d で新規導入する形に再構成 |

---

## KL-13: Lessons Learned

### KL-13-1: Pedagogical chapter ordering の自然な軸
Part 2「数値アルゴリズム」の内部構造には「**一様で構築 → 非一様で拡張**」という
自然な pedagogical 軸が存在する．§6 を中央に挟む配置は読者を「一様 ↔ 非一様」を
反復横断させ認知負荷が高い．末尾配置で「Part 2 = 一様格子完成形 + 非一様拡張」
という構造を一目で読者に伝える．Part の pedagogical role を明示的に設計する重要性．

### KL-13-2: Forward-ref severity 3 階層分類
章順序変更時の forward-ref 処理は単一規則ではない．以下 3 階層で判別:
- **(a) 純粋予告段落** — moved chapter が後で出現するなら DELETE
- **(b) 章間 transition** — 「次章では…」型は REWRITE で次章対象を更新
- **(c) scheme 統合 context** — scheme 固有の議論は KEEP (移植すると重複生成)

(a)(b)(c) を機械的に区別せずまとめて「移植」しようとすると narrative が壊れる．

### KL-13-3: 章番号 textual hardcode の捕捉
`\ref{}` は LaTeX が自動更新するが，以下 3 種は手動更新必要:
- (i) `tab:chapter_overview` 等の章番号列（表セル内 hardcode）
- (ii) `(§7.3)` 等 parenthetical 数字（本文中の inline 章番号）
- (iii) 「で構築した」等 **時制 framing**（forward-ref に対し過去形は論理破綻）

CHK-218 では (iii) を 08 L6 で発見し framing 修正．章順序変更時の grep 戦略は
`\\ref{}` 以外を 3 種すべて検査．

### KL-13-4: Part 構造の pedagogical role
Part 2 = §4 基底（CCD 演算子） → §5 時間骨格 → §6-§8 物理項適用（移流・圧力連成・PPE）
→ §9 拡張（非一様）の 4 段階構造．§9 を「拡張章」として明示的に最後に置くことで
「Part 2 内部 = 完成形 + 拡張」 の階層が読者に伝わる．Part の構造論理を
chapter ordering で表現する設計判断の事例．

### KL-13-5: 削除と spillover の検出
Phase 2 で subsubsection ブロック (03d L226-243) を削除したが，章末「本節の要点」
リストの 1 行 bullet (L257) が残存していた．V-grep で初めて検出．
**教訓**: 大きな削除を行った後は，関連 keyword を全 .tex 横断 grep で
spillover 残存をチェックすること．Phase 6 build verify を「単なるビルド成功確認」
ではなく「論理整合性の最終 gate」として機能させる．

---

## 未完事項 / Out of Scope

- §7-§9 内 scheme 固有非一様議論（07_advection L38- 等）の §6 移植 — 別 task
- main へのマージ — ユーザ判断待ち（本 worktree 継続使用）
- 数値検証実行 — 別 task (CHK-216 持越)
- §11+ 検証実装 — 別 task (CHK-216 持越)

---

## Commits (chronological)

```
46ad1ae paper: §6 (interface-fitted non-uniform grid) を Part 2 末尾に移動
7cf0dd0 paper: 純粋予告段落 + sketch subsubsection を一括削除 (CHK-218 Phase 2)
edae99c paper: §5 章末 transition + §7 framing を §6 移動に整合 (CHK-218 Phase 3)
69f32f3 paper: tab:chapter_overview 行入替 + textual 章番号更新 (CHK-218 Phase 4)
94611f1 paper: Phase 5 — sync % comment chapter numbers for §6 relocation
e2fae70 paper: drop §3.4 D1-D4 summary bullet (Phase 2 spillover)
```

(+ this memo + ledger update commit)
