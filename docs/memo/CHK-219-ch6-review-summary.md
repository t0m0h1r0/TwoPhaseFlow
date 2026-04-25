# CHK-219 — §6 (移流章) 査読官視点レビュー + ch13 production stack 整合

**Branch**: `worktree-ra-paper-ch4-rewrite`
**Date**: 2026-04-26
**Phase**: PAPER_CH6_REVIEW
**Predecessor**: CHK-218 (§6 を Part 2 末尾へ移動)

---

## Trigger

ユーザ指摘: 「6 章について査読官になったつもりで厳正にレビューを行って」+ 3 件具体懸念:

1. §6.1 に非一様格子 CLS が残存 — §9 (新 §6 grid 章) へ追い出すべき
2. §6.2.3 / §6.4 で DCCD 記述が残存 — 「フラックスが必要なら FCCD，風上による安定化が必要なら UCCD を使う方針」に書換
3. §6 各節の Part 1 由来が分かりづらい — Part 1 inheritance 宣言を追加

User AskUserQuestion 回答:
- DCCD 置換戦略: 「ch13/ の実験内容を見て」 (実装に合わせる)
- §6.1 移動 scope: 「T1-T3 全部 §9 へ」

---

## 探索 — ch13 production stack 調査

`experiment/ch13/config/*.yaml` (production):
- ψ 移流: **fccd** (`FCCDLevelSetAdvection`)
- 運動量移流: **uccd6** (`UCCD6ConvectionTerm`)
- 再初期化: **ridge_eikonal** (`RidgeEikonalReinitializer` — DCCD 圧縮項を**使わない**)
- PPE: **fccd** (`PPESolverFCCDMatrixFree`)

DCCD ベース実装 (`DissipativeCCDAdvection` / `SplitReinitializer` / `DCCDPPEFilter`) は src/ に残存だが ch13 production 非使用. Ridge-Eikonal は §3.4 で Part 1 既出.

→ **論文 §6 が実装の実態と乖離**. 本 task は narrative を実装に追随させる修正で，src/ コード変更は一切不要.

---

## Phase 内訳 (6 paper commit + 1 ledger commit)

| Phase | Commit | 内容 | LOC (±) |
|---|---|---|---|
| 1 | 8db3489 | §6 章ヘッダ Part 1 inheritance + §6.0 PROD 整合 | ±25 |
| 2 | 42bf8a6 | §6.1 (T1-T3) を §9 へ移動 + §6.1 削除 | -58 / +43 |
| 3 | 85c0a55 | §6.2.3 DCCD → FCCD 書換 + box:scheme_roles 整合 | ±100 |
| 4 | 2750edd | §6.4 を Ridge-Eikonal 主軸に転換 (Split は legacy) | ±70 |
| 5 | 535b5d0 | §6.3/§6.5/§6.6 Part 1 inheritance | ±22 |
| 6 | d2224c0 | 安定性制約 \subsection → \subsubsection 降格 | ±5 |
| 7 | (本 commit) | LEDGER 更新 + KL-14 lessons memo | — |

### Phase 1 — §6 章ヘッダ + §6.0 narrative 更新
- §6 章タイトル副題から DCCD を外し「FCCD/UCCD6/Ridge-Eikonal の ch13 production stack」に変更
- §6 章ヘッダ直後に `Part 1 連続定式化との関係` itemize ブロック新設 (§2 NS / §3.2 cls_advection / §3.3 reinit / §3.4 ridge_eikonal の 4 axis)
- §6 ToC enumerate から §6.1 行を削除 (Phase 2 で実体削除)
- §6.0 (07_0_scheme_per_variable) で ψ 行 `Dissipative CCD` → `FCCD（FCCDLevelSetAdvection；ch13 production）`
- bulk 速度 `DCCD または UCCD6` → `UCCD6 のみ；DCCD は legacy 注記`

### Phase 2 — §6.1 (T1-T3) を §9 へ移動 + §6.1 削除
- §6.1 sec:cls_on_nonuniform subsection 全 59 行削除
- T1 (ξ 空間フィルタ順序) → 06b_ccd_extensions sec:ccd_metric 末尾に新規 \subsubsection で移植
- T2 (ψ 線形補間根拠) → 06_grid 既存 tcolorbox に質量誤差比較含めて inline 統合
- T3 (空間可変 Heaviside ε(x)) → 06_grid 末尾 sec:grid_ale 後に新規 \subsection として移植
- T4 (DCCD 強度設計) → §6.2.2 統合後 Phase 3 で削除
- 外部参照保護: `\phantomsection\label{sec:cls_on_nonuniform}` を T1 移植先 (06b) に設置 → 4 件全件保護 (14_conclusion / 12g_nonuniform_grid ×3)
- T3 の labels (eq:eps_xi_cells / box:eps_xi_csf_warning) は移植先 (06_grid) でそのまま維持

### Phase 3 — §6.2.3 DCCD → FCCD 書換
- 節タイトル「Dissipative CCD の採用：フィルタによるスペクトル安定化」 → 「FCCD 面値演算子の採用：保存型フラックスによる安定化」
- 約 140 行 DCCD スペクトル散逸論述を以下に書換:
  1. FCCD ψ 移流の離散化 (面値演算子 P_f / 面フラックス (ψu)_f)
  2. 安定化機構 (面値評価が振動源を切る理由)
  3. 質量保存性 (FCCD 保存型面フラックスのテレスコーピング)
  4. ψ clamp (既存内容保持)
  5. CFL bound box
- DCCD 旧叙述は footnote 1 件 (§4 sec:dissipative_ccd 参照) に圧縮
- box:scheme_roles の CLS 移流行を `Dissipative CCD…` → `FCCD（面値保存型；§sec:fccd_advection）` に同調
- backward-compat label (sec:advection_dccd_design / result:dccd_stability / eq:psi_clamp / alg:dccd_adv / warn:adv_clamp / eq:dccd_adv_ccd / eq:dccd_adv_filter) は全件維持

### Phase 4 — §6.4 を Ridge-Eikonal 主軸に転換
- subsection タイトル「CLS 再初期化：圧縮項の Dissipative CCD スキーム」 → 「CLS 再初期化：Ridge-Eikonal 主軸（ch13 production stack）」
- Part 1 inheritance + 構造リスト (Ridge-Eikonal 主軸 / 過渡 Eikonal 法 / 旧実装 Split) 追加
- 旧 SplitReinitializer 法説明を `\paragraph{旧実装（SplitReinitializer）：圧縮項の DCCD 離散化}` 見出し下に降格 + `\phantomsection\label{sec:cls_compression_legacy}` 設置
- sec:eikonal_reinit / sec:xi_sdf_reinit に Ridge-Eikonal 連続定式化 (§3.4) からの離散実装宣言を 1 文ずつ追加
- box:scheme_roles の CLS 圧縮 2 行 (移流部 + 拡散部) を CLS 再初期化 (Ridge-Eikonal) 1 行に統合
- sec:cls_compression label は subsection L5 で維持 (外部参照保護)

### Phase 5 — §6.3/§6.5/§6.6 Part 1 inheritance
各 subsection 冒頭に「Part 1 連続定式化との関係」ブロック追加:
- §6.3 (07c FCCD 移流): §2 NS 運動量移流項の Balanced-Force 整合離散化／ch13 production の UCCD6ConvectionTerm 主実装との関係
- §6.5 (07d CLS A→F): §3.2 cls_advection + §3.3 reinit からの離散化／Stage A FCCD + Stage C Ridge-Eikonal が ch13 主経路
- §6.6 (07e 粘性 3 層): §2 onefluid 粘性項 ∇·(2μD) の Layer A/B/C 分解／式 jump_stress の応力ジャンプ条件が設計根拠

### Phase 6 — 安定性制約 \subsection → \subsubsection 降格
- 07b L639 `\subsection{安定性制約（時間刻みの決定）}` → `\subsubsection` に降格
- 07b 内 subsection 階層重複 (CLS 再初期化 + 安定性制約) を解消し，§6.4 内の subsubsection として §6.4.x 章番号正常化
- §6 章ヘッダ enumerate を更新 — sec:stability を独立 item から §6.4 description 内末尾文に統合
- sec:stability label は維持 (外部参照 5 件: 14_conclusion / 08_collocate / 02b_surface_tension / 10b_dccd_bootstrap ×2 はすべて \\ref 経由で動的解決)

---

## Verification

### V-grep (V-1 〜 V-5)
| # | Check | Result |
|---|---|---|
| V-1 | `grep -c "^\subsection" 07b_reinitialization.tex` | 1 ✓ |
| V-2 | `sec:cls_on_nonuniform` 全 5 件 (06b phantom + 14_conclusion + 12g ×3) | 全件解決 ✓ |
| V-3 | §6 ファイル内「本稿は…DCCD」「採用…DCCD」 | 0 件 ✓ |
| V-4 | §6 ファイル内 `sec:onefluid \| sec:cls_advection \| sec:reinit \| sec:ridge_eikonal` 参照 | 14 箇所 ✓ |
| V-5 | 07_advection 内 FCCD / UCCD6 / Ridge-Eikonal 言及 | 多数 ✓ |

### Build (V-6 / V-7)
- latexmk -xelatex main.tex: clean (0 undef refs / 0 multiply defined / 0 LaTeX errors)
- page count: **257 pp** (target 256±5 内 ✓)

---

## KL-14 Lessons (4 件)

### KL-14-1: Narrative ↔ implementation 整合性チェック
論文書換 task では `experiment/<chN>/config/*.yaml` の scheme key を参照して実装の確立状態を確認するステップを Phase 1 探索に組み込む.

「論文先行 → 実装後追い」 vs 「実装先行 → 論文後追い」 で書換戦略が逆転する:
- 論文先行: 実装側が paper を仕様書として追従 (`src/twophase/` の class 名／メソッド名を paper 既出語と一致)
- 実装先行 (本 task): paper 側が production の実装をスナップショットとして記述 (config YAML の `algorithm: ridge_eikonal` 等の key 値を paper narrative と一致)

CHK-219 は後者で，ch13 production stack の確立 (CHK-186 系列) から半年以上経過した結果，論文 §6 の DCCD 主軸記述が実装の Ridge-Eikonal 主軸と乖離していた. 査読官指摘で発覚.

**ガード**: paper review task の探索 phase で必ず以下を実施:
```bash
grep -h "algorithm:" experiment/ch{N}/config/*.yaml | sort -u
grep -h "spatial:" experiment/ch{N}/config/*.yaml | sort -u
```
で production scheme 配分を一覧し，paper §N narrative と照合.

### KL-14-2: Forward-ref label 移動の `\phantomsection` パターン
外部参照されているラベルを物理的に移動する場合，移動先に `\phantomsection\label{旧ラベル}` を設置することで全外部参照を破壊せず移動可能.

**本 task の適用例**: `sec:cls_on_nonuniform` (旧 §6.1)
- 移動前: 07_advection L42 の subsection label
- 移動先: 06b_ccd_extensions L20 (新規 \subsubsection の直下に phantomsection)
- 外部参照 4 件 (14_conclusion / 12g ×3) は全件 \ref{sec:cls_on_nonuniform} のまま自動解決

**注意点**:
1. phantomsection は `\subsubsection` の本物の label (sec:ccd_metric_filter_order 等) と並列して 2 つ目の label として設置可能
2. コメントで `% backward-compat: 旧 §X.Y ラベル．他章の参照保護．` と明示
3. CI 等で「孤立 label」検出 lint がある場合は除外設定

**比較**: `sec:cls_compression_legacy` (Phase 4 で SplitReinitializer 降格時に新設) は phantomsection ではなく \paragraph 直下の通常 label として設置. 旧ラベル sec:cls_compression は subsection L5 で維持. 既存ラベル維持 + 新ラベル追加 のパターン.

### KL-14-3: \subsection 階層重複と LaTeX 章番号付け
1 ファイル内に複数の `\subsection` があると LaTeX は同階層として連番を振るため章順序が予期せず変化.

**本 task の症状**: 07b_reinitialization.tex に 2 つの \subsection (L5: CLS 再初期化 + L639: 安定性制約) があった. CHK-218 で §6 が Part 2 末尾に移動したことで番号付けが変化し，§6.4 (再初期化) と §6.5 (安定性) が独立 subsection として並列化していた. しかし narrative 上は安定性制約は再初期化の付属事項であるべき.

**Phase 6 の解消手順**:
1. 07b L639 `\subsection` → `\subsubsection` 降格 (label sec:stability は維持; 外部参照 5 件は \ref で動的解決)
2. §6 章ヘッダ enumerate (07_advection L42-46) を更新: sec:stability を独立 item から §6.4 description 末尾文に統合

**教訓**: 1 .tex ファイル ≈ 1 \subsection を原則とする. 複数 \subsection が必要なら別ファイルに分離. 既存複数 \subsection を発見したら build PDF の TOC で章番号がユーザ意図通りか目視確認.

### KL-14-4: Part 1 inheritance 宣言の効果
各 subsection 冒頭の 1-2 文で「本節は §X で導出した eq:Y を §Z の数値スキームで離散化する」と明示するだけで読者負担激減.

**本 task で導入したパターン**:
```latex
\noindent\textbf{Part 1 連続定式化との関係：}
本節は §~\ref{sec:cls_advection}（§3.2 CLS 保存形移流方程式）と
§~\ref{sec:reinit}（§3.3 再初期化方程式）で確立した連続定式化を
1 物理時間ステップの演算子分裂に組み込む離散アルゴリズムを示す．
```

**効果**:
- 査読官 / 読者が §6 の各 subsection を独立に読み始めても，「これは §3 のどの式の離散化か」が即座に分かる
- 「§4-§5 章ヘッダと比較して §6 は Part 1 inheritance が薄い」という査読官指摘 (Concern 3) を是正
- 同じパターンを §3.4 (ridge_eikonal) や §2 (onefluid) など Part 1 主要 label への参照で他章にも展開可能

**展開推奨**: Part 1 inheritance 宣言を以下にも追加検討:
- §7 collocated grid 章: §2.1 (notation) + §2.4 (NS_onefluid) からの離散化宣言
- §8 PPE 章: §2.4 onefluid 圧力方程式 + §3.5 GFM 連続式からの離散化宣言
- §9 grid 章: §2.1 notation + §3.2 CLS の非一様拡張宣言

---

## Out of Scope

- DCCD 関連 src/ コード削除 (`DissipativeCCDAdvection` / `SplitReinitializer` / `DCCDPPEFilter`) — 互換テスト・legacy パスのため src/ 残存
- DCCD 圧縮の付録 H 物理移動 (Phase 4 では `\paragraph` 降格 + footnote 化に留める)
- §6.3 FCCD 節を ψ 移流まで拡張統合 (現状は運動量のみ; ψ 移流は §6.2 に独立記述で運用)
- main へのマージ (Phase 7 完了後にユーザ判断; 本 worktree 継続)
- 数値検証実行・新規実験追加

---

## Pending User Decision

- main へのマージ (no-ff 推奨; CHK-219 の 6 paper commit + 1 ledger commit を 1 merge commit に集約)

ユーザ指示があれば本 worktree から main へ no-ff merge を実施.
