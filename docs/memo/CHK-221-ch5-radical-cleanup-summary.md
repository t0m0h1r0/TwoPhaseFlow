# CHK-221 — §5 Option A radical cleanup 完了サマリ

**Date**: 2026-04-26
**Phase**: PAPER_CH5_RADICAL_CLEANUP
**Branch**: worktree-ra-paper-ch4-rewrite
**Predecessor**: CHK-220 (§5 per-term 再編 + ch13 production stack 整合)

---

## 1. Trigger

CHK-220 完了後の追加査読でユーザより 5 件の懸念が提示された：

1. **LS/CLS の時間発展の記載がない** — TVD-RK3 generic *q* 変数で ψ^{n+1} 独立式番号なし．
2. **陰解法と陽解法の説明が見当たらない** — 各 per-term 散発; 系統的導入節不在．
3. **安定性 / CFL の理論体系の説明がない** — A-stable per-term 言及のみ; CFL 数定義式不在; von Neumann / G(θ) / ζ 平面 / L-stable 系統不在．
4. **旧解法が残っている** — AB2+IPC legacy 38 LOC + CN legacy 21 LOC + §5.8 表 legacy 列 + 4 phantomsection．
5. **Level についての記載が残っている** — §5 内 22 箇所 + §5.10 補足節 33 LOC + §10_3 が sec:time_level{2,3,_legacy} を 3 件参照．

ユーザは **Option A radical complete deletion** を選択：legacy 完全削除 + 外部参照書換 + Level 概念名完全撤去 + §10_full アルゴリズム表 ch13 化．

---

## 2. Phase 別作業内訳

| Phase | 主要作業 | §5 LOC delta | 他章 | commit |
|---|---|---|---|---|
| 1 | §5 章 intro 「時間積分の 3 形式」段落 + §5.1 タイトル変更 + 2 新 subsubsection (時間積分形式の分類 + 精度整合性と零安定性の基礎) | +35 | 0 | (Phase 1-2 統合 commit) |
| 2 | §5.2 末尾に 2 新 subsubsection (sec:cfl_definitions + sec:von_neumann) | +30 | 0 | (Phase 1-2 統合 commit) |
| 3 | §5.3 内 eq:cls_tvd_rk3_psi 追加 + §5.5/§5.7 ψ 先行確定言及 | +20 | 0 | (Phase 3 commit) |
| 4 | §5 AB2+IPC legacy paragraph 完全削除 + bdf2_startup warnbox 新設 + §5.8 表 legacy 列削除 + 外部参照 4 箇所書換 (§08b L16/L88, §11f L89, §appendix_ppe_pseudotime L386) | -53 | -4 | (Phase 4 commit) |
| 5 | §10_full_algorithm.tex 全面書換 (アルゴリズム表 + notation + predictor body + warn:bdf2_startup rename) | 0 | rewrite | (Phase 5 commit) |
| 6 | §5 CN legacy paragraph 完全削除 + §5.3/§5.4 安定性 paragraph に \ref 紐付け + §08c L102 参照書換 | -15+6 | -1 | (Phase 6 commit) |
| 7 | §5 Level 表記 22 箇所書換 (sec:time_level1 のみ §5.3 backward-compat alias 残置) + §5.10 削除 → §10_3 redirect 文に置換 + §10_3 L11/L182/L223 dangling refs 解消 | -75 | rewrite | (Phase 7 commit) |
| 8 | V-1..V-11 verify + LEDGER + memo + commit | 0 | +memo | (Phase 8 commit) |

**§5 終状 LOC**: ~970 (CHK-220 終状 841 から +129; intro/理論節 +85, ψ +20, \ref +6, legacy/Level 削除 -75 = net +36 + 理論節定義表 +93)

---

## 3. 採択判断 (Option A vs B)

| 項目 | Option B (互換性重視) | Option A (radical, 採択) |
|---|---|---|
| legacy paragraph | phantomsection で隠蔽保持 | 完全削除 + 外部参照書換 |
| §5.8 表 legacy 列 | 残置 | 削除 (lccc → lcc) |
| Level 概念名 | §5.10 補足節で位置づけ説明 | §5.10 削除 + §10_3 redirect |
| §10_full algorithm 表 | AB2+CN 既存 | IMEX-BDF2 + ch13 stack へ全面書換 |
| 外部参照コスト | 0 (phantomsection 透過) | 5 ファイル / 8 件書換 |
| 査読官印象 | 「過渡期」感 | 「production」感 |

ユーザ選択理由: ch13 production stack に確定したので過渡期記述は不要 + 査読時の「では旧版は何のために残したのか」誘発を回避 + paper を読み込む側のストレス削減．

---

## 4. KL-16 系 Lessons Learned

### KL-16-1: legacy paragraph 完全削除の外部参照書換コスト試算

phantomsection 設計は外部参照を保護するが，「実装ファイル整理」でも参照ファイル数 × 参照箇所数のコストがそのまま発生する：

- 本件では 5 ファイル / 8 件参照 (eq/sec/warn 3 種類) を一括書換
- 1 ファイル 1 行平均 ~3 分 → 計 ~24 分の追加工数
- ただし xelatex 検証 (各 Phase 末 2 pass) で undef refs を即時検出可能

**結論**: phantomsection は「短期保護」用途に限定し，「最終版出版前」では Option A 推奨．

### KL-16-2: phantomsection 廃止と「概念名 \ref を主軸節へ集約」のトレードオフ

| 軸 | Option A (集約) | phantomsection (旧) |
|---|---|---|
| 参照透過性 | 高 (sec:time_level1 = §5.3 ch13 IMEX-BDF2 = 1 対 1) | 低 (sec:time_level2 → 削除済み §5.4 を指す) |
| 旧版互換性 | 低 (古い PDF とラベル不整合) | 高 (古い \ref がそのまま) |
| 査読官の精神コスト | 低 (1 概念 1 ラベル) | 高 (「では Level 2 とは何か」探索) |
| 実装変更時のメンテ | 低 (ラベル名と内容が乖離しない) | 高 (古いラベル名 + 新内容 の二重管理) |

**結論**: 「概念名 vs 主軸節名」が乖離した時点で phantomsection は技術的負債．Option A で集約．

ただし sec:time_level1 のみは §5.3 backward-compat alias で残置 (FCCDLevelSetAdvection class 名と整合; rename は CHK-222 で別途検討)．

### KL-16-3: 安定性 / CFL 理論節を per-term の前段に配置するか後段にするかの判断

本件では **§5.1/§5.2 (前段) 配置** を採択：

- 前段配置のメリット: per-term 節 (§5.3-§5.7) で「§\ref{sec:cfl_definitions} と §\ref{sec:von_neumann} の枠組みで」と後方参照のみで議論を閉じる; per-term 節の安定性 paragraph が短文で済む (各 ~5-10 LOC)
- 前段配置のデメリット: 読者は理論節を読まないと per-term 節の安定性議論が浮く; ただし \ref で誘導可能
- 後段配置 (代替案) のデメリット: per-term 節で同じ用語を繰り返し定義する; per-term 節長が膨張

**結論**: 査読官視点では「先に体系，次に各論」が自然．Hairer-Wanner 教科書も同型．

### KL-16-4: アルゴリズム全体表 (§10_full) と章別主軸 (§5) のドリフト検出

CHK-220 で §5 を ch13 化したが §10_full が AB2+CN のままだった事象が発生 (CHK-221 Phase 5 で発覚)．再発防止策：

- 章別改稿時に \ref 影響範囲 grep を必須化 (`grep -rn "sec:ab2_ipc" paper/sections/` 等)
- §10_full は「全体図鑑」として §5/§6/§7 等の主軸節と意味的同期する責務がある → CHK-N 完了時の V-grep に「§10_full との意味的同期」を含める
- 本件の V-8 (§10_full IMEX-BDF2 mention 数) はこの同期を機械的に確認する

---

## 5. V-grep 結果

| # | 検証 | 期待 | 実測 | 状態 |
|---|---|---|---|---|
| V-1 | `grep -cn "Level" §5` | 1 (= FCCDLevelSetAdvection class 名) | 1 | PASS |
| V-2 | dangling sec:ab2_ipc/time_cn/time_level{2,3,_legacy} | 0 | 0 | PASS |
| V-3 | dangling warn:ab2_startup/eq:predictor_ab2_ipc/eq:crank_nicolson | 0 | 0 | PASS |
| V-4 | §5 intro (L1-100) IMEX/陽/陰 mention | ≥3 | 17 | PASS |
| V-5 | eq:cfl_number 存在 + §5 内参照 | ≥1 | 2 (label + ref) | PASS |
| V-6 | eq:cls_tvd_rk3_psi 存在 + 外部参照 | ≥2 ファイル | 2 (§5 + §10_full) | PASS |
| V-7 | §5.8 表 lcc 3 列 | OK | OK (L825) | PASS |
| V-8 | §10_full IMEX-BDF2/ch13 mention | ≥3 | 4 | PASS |
| V-9 | §10_3 残 §5 ref 全て live | OK | 3 件 (sec:time_int / sec:time_capillary / sec:time_level1) 全 live | PASS |
| V-10 | xelatex 2-pass 0 undef / 0 multiply | OK | 0 / 0 | PASS |
| V-11 | PDF page count vs CHK-220 (259 pp) | ±5 pp | 260 pp (+1) | PASS |

---

## 6. Out of Scope

- §10_3 (Level selection) 自体の改稿 — CHK-222 以降で別途検討
- 付録 `app:cn_adi_detail` の完全削除 — §10_full から参照削除のみ実施
- prompts/agents-claude/* の Level 概念名整理 — paper 責任範囲外
- src/twophase/ の cn_adi 実装本体 — paper 改稿のみ; PR-5 algorithm fidelity 維持
- ch13 YAML 改訂 — paper 記述のみ; YAML は ch13 production stack 現状維持
- main マージ — ユーザ確認後

---

## 7. 次回 CHK 候補

- **CHK-222 候補 A**: §10_3 (Level selection) 自体の改稿 — Level 概念名を実装トリガーレジーム (剛性レジーム) に rename
- **CHK-222 候補 B**: sec:time_level1 backward-compat alias の rename → sec:time_advection_main + §10_3/§10_full/§11f/§appendix_ppe_pseudotime 5 箇所書換
- **CHK-222 候補 C**: §5 V-12 候補 — §5 内の旧用語 (AB2/CN) 完全 grep 0 確認 (本件で legacy 削除したが paragraph 中の解説的言及は残存可)
