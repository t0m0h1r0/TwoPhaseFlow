# CHK-215 — Part 1/2/3 ナラティブ整合構造リファクタ完了メモ

- **Date**: 2026-04-25
- **Branch**: `worktree-ra-paper-restructure-part123`
- **Commits**: 8 phase commits (Phase 1..8) + 1 ledger commit
- **Build**: xelatex clean, 257 pp, 0 undef refs, 0 multiply defined labels
- **V-grep**: V-1..V-8 全 pass

## 1. 趣旨

CHK-205..213 が論文の **内容 defect** (Critical/Major/Minor) を 9 passes で完全 saturation 解消したのに対し，本 CHK-215 は **構造的逸脱** に焦点を絞ったリファクタ task．

ユーザは §1-§13 を以下の Part 構造で位置付けている：

- **Part 1 (§1-§3)**: NS 方程式・LS 法など基礎物理学・数学に近い内容
- **Part 2 (§4-§9)**: 離散化手法 (CCD/FCCD/DCCD/UCCD6/PPE 離散化等)
- **Part 3 (§10-§13)**: それまでの内容を統合し，安定計算をさせる方法およびその実験

3 並列 Explore agent (§1-§3 / §4-§9 / §10-§13) が **12 件の deviation** を抽出．本 task で全件解消し，読者が論文を Part 1 → 2 → 3 の順で素直に読めるよう構造を厳格化した．

## 2. Before/After Part 構造図

### Before (CHK-215 着手前)

```
Part 1 (§1-§3) — 基礎物理／数学
  §1 Introduction
    + Glossary tcolorbox (FCCD/UCCD6/DCCD パラメタ)         ← α-1 (離散化詳細; Part 2 へ)
    + 技術要素列挙 (CCD/DC k=3/分相 PPE 仕様)                ← α-2 (離散化詳細; Part 2 へ)
  §3 CLS 法
    + 仮想時間刻み Δτ 安定性 (DCCD/CN/TVD-RK3)              ← α-3 (再初期化詳細; Part 2 §7b へ)
    + Ridge-Eikonal D1-D4 数学的定義                        ← α-4 (非一様格子拡張; Part 2 §6d へ)
    + 再初期化実装ガイド・収束判定閾値                        ← α-5 (実装指針; Part 2 §7b へ)

Part 2 (§4-§9) — 離散化
  §5 Time Integration
    + Level 3 routing 閾値段落                              ← β-1 (Level routing; Part 3 §10_3 へ)
  §7e Viscous 3-layer
    + CN 粘性 Helmholtz + DC 呼び出し順                     ← β-2 (アルゴリズム手順; Part 3 §10 7-step へ)
  §9d Defect Correction
    + Level 1/2/3 純 FCCD 収束率表                          ← β-3 (Level 比較; Part 3 §10_3 へ)
  §9f Pressure Summary
    + Level 比較表 + GPU 二路選択                            ← β-4 (Level routing; Part 3 §10_3 へ)

Part 3 (§10-§13) — 統合・実験
  §10b DCCD Bootstrap
    + DCCD 散逸強度設計 (eq:eps_max)                        ← γ-1 (離散化定義; Part 2 §4c へ)
    + DCCD 適応制御 (alg:dccd)                              ← γ-2 (離散化定義; Part 2 §4c へ)
    + Bootstrap (付録 H と完全重複 49 LOC)                   ← γ-3 (削除; phantom 残置)
  §10_5 Pure FCCD DNS
    + Phase 2/3 (HFE upwind + 粘性 DC) 詳述定式             ← γ-4 (詳述; Part 2 §7c/§7e への ref に圧縮)
  §13 Benchmarks
    + 浮力分解の再掲 (10 行 LaTeX block)                     ← γ-5 (Part 1 §2 への 1 行 ref に圧縮)
```

### After (CHK-215 完了後)

```
Part 1 (§1-§3) — 基礎物理／数学 (純化)
  §1 Introduction
    → 概要文 + pointer (詳細は §4 sec:notation_glossary / sec:tech_roadmap 参照)
  §3 CLS 法
    → 保存形界面追跡・再初期化方程式・曲率の数学的基礎のみ
    → §3d 末尾に sec:ridge_eikonal_nonuniform 残置 (理論側 anchor; D1-D4 数学定義は §6d)

Part 2 (§4-§9) — 離散化 (拡充)
  §4 CCD ★ NEW 冒頭
    + sec:notation_glossary (記号と略語)                    ← α-1 移動先
    + sec:tech_roadmap (技術要素一覧)                       ← α-2 移動先
  §4c DCCD Derivation ★ NEW 末尾
    + sec:dccd_params (DCCD パラメータ設計と適応制御)       ← γ-1, γ-2 移動先
    + eq:eps_max, eq:adaptive_eps, alg:dccd
  §6d Ridge-Eikonal Nonuniform ★ NEW 冒頭
    + sec:ridge_nu_d1d4_math (D1-D4 数学的定義)             ← α-4 移動先
  §7b Reinitialization ★ NEW 末尾
    + 仮想時間刻み Δτ 安定性 (warn:cls_dtau_stability)      ← α-3 移動先
    + 再初期化実装ガイド・収束判定閾値                       ← α-5 移動先
  §9d/§9f
    → §9d 表は §10_3 へ移動; §9f tab:accuracy_summary は 9 cross-ref のため残置 (R-1)

Part 3 (§10-§13) — 統合・実験 (純化)
  §10_3 Level Selection ★ 集約
    + sec:level_selection (Level 1/2/3 routing 閾値)        ← β-1 移動先
    + sec:dc_pure_fccd_convergence (純 FCCD DC 収束率表)    ← β-3 移動先
    + sec:level_gpu_dual_path (GPU 二路選択)                ← β-4 GPU 段落移動先
  §10_full_algorithm Step 5 ★ 拡張
    + CN 粘性 Helmholtz + DC 呼び出し順 enum                ← β-2 移動先
  §10b DCCD Bootstrap → §10b Time Step Control
    → §4c への pointer + sec:bootstrap + sec:algo_timestep のみ
    → DCCD 散逸強度・適応制御は §4c へ集約完了
  §10_5 Pure FCCD DNS
    → Phase 2/3 詳述は §7c/§7e への ref に圧縮 (eq:pure_fccd_hfe_upwind, eq:pure_fccd_viscous_dc は残存)
  §13 Benchmarks
    → 浮力分解は §2 sec:two_to_one への 1 行 inline ref
```

## 3. Deviation 解消一覧 (12 件全件)

| # | 移動元 | 移動先 | 内容 | Phase | Commit |
|---|---|---|---|---|---|
| α-1 | §1 L14-33 | §4 冒頭 sec:notation_glossary | Glossary tcolorbox | 3 | fcebd54 |
| α-2 | §1 L43-87 | §4 冒頭 sec:tech_roadmap | 技術要素列挙 | 3 | fcebd54 |
| α-3 | §3b L284-319 | §7b 末尾 | 仮想時間刻み Δτ 安定性 | 2 | b2e100a |
| α-4 | §3d L226-355 | §6d 冒頭 sec:ridge_nu_d1d4_math | D1-D4 数学的定義 | 2 | b2e100a |
| α-5 | §3b L247-281 | §7b 末尾 | 再初期化実装ガイド | 2 | b2e100a |
| β-1 | §5 L523-563 | §10_3 sec:level_selection | Level 3 routing 閾値 | 4 | b63ddfb |
| β-2 | §7e L178-215 | §10 7-step Step 5 | CN 粘性 + DC 呼び出し順 | 4 | b63ddfb |
| β-3 | §9d L200-224 | §10_3 sec:dc_pure_fccd_convergence | 純 FCCD 収束率表 | 4 | b63ddfb |
| β-4 | §9f L119-130 | §10_3 sec:level_gpu_dual_path | GPU 二路選択 (R-1: 表/box は残置) | 4 | b63ddfb |
| γ-1 | §10b L41-58 | §4c 末尾 sec:dccd_params | DCCD 散逸強度設計 (eq:eps_max) | 5 | 82e6994 |
| γ-2 | §10b L59-136 | §4c 末尾 sec:dccd_adaptive | DCCD 適応制御 (alg:dccd) | 5 | 82e6994 |
| γ-3 | §10b L137-185 | (削除) | Bootstrap 49 LOC; 付録 H への ref | 1 | c8f70fe |
| γ-4 | §10_5 L81-132 | §7c/§7e への ref | Phase 2/3 詳述定式 (圧縮) | 6 | cc58ff0 |
| γ-5 | §13 L127-135 | §2 sec:two_to_one への 1 行 ref | 浮力分解再掲 | 7 | 250cb9f |

## 4. Risk Mitigation 達成状況

| Risk | Mitigation | 結果 |
|---|---|---|
| **R-1** sec:pressure_accuracy_summary 9 件 cross-ref 漏れ | §9f の tab:accuracy_summary + box:ppe_design_rationale を**残置**; β-4 は GPU 段落のみ移動 | ✓ 全 9 件 ref 維持 |
| **R-2** sec:bootstrap 削除後の build break (3 件 cross-ref) | Phase 1 で sec:bootstrap label を §10b 内維持; 重複内容のみ削除 | ✓ 3 件全件解決 |
| **R-3** §6d 既存内容との重複 | §3d=理論層 / §6d=実装層 の split を確認; 数学定義は §6d 冒頭新設 subsubsection に挿入 | ✓ 重複ゼロ |
| **R-4** §10_3 肥大化 (+280 LOC) で読みにくい | sec:level_selection / sec:dc_pure_fccd_convergence / sec:level_cost_accuracy / sec:level_gpu_dual_path の 4 subsection で構造化 | ✓ 読みやすさ確保 |
| **R-5** Phase 7 §1b roadmap 更新漏れ | Phase 1-6 完了後に Ch4/Ch6/Ch10 の overview 表を Part 構造変更に同期 | ✓ 同期完了 |
| **R-6** CHK-213 saturation 宣言との整合 | CHK-215 は新規エントリ; CHK-213 を prev_CHK 降格; 内容 defect ではなく構造のみ | ✓ 矛盾なし |
| **R-7** Phase 失敗時の rollback | 各 phase 独立 commit; 部分 revert 可能 | ✓ Phase 8 で重複 label を最小修正でカバー |
| **R-8** LOC 規模 | Net ≈ +0 LOC (移動主体); 削除 -49 (γ-3) + 圧縮 -10 (γ-5) | ✓ 推定通り |

## 5. V-grep 検証結果 (Phase 8)

| # | 検証項目 | 結果 |
|---|---|---|
| V-1 | `\ref{sec:bootstrap}` 件数 | 3 件全件解決 (10_full_algorithm L19, 06_grid L255/L276) |
| V-2 | `warn:cls_dtau_stability` 出現箇所 | §7b L555/L590 (定義) + §3b L251 (note) のみ |
| V-3 | `sec:ridge_eikonal_nonuniform` 出現箇所 | §3d L227 (定義) + §6d L12 + §10_5 L76 |
| V-4 | `sec:dccd_params` 出現箇所 | §4c L208 (定義) + §10/§4/§10b/§9 計 5 ref |
| V-5 | `sec:pressure_accuracy_summary` 出現箇所 | §9f L8 (定義) + 9 ref (R-1 ゼロ削除維持) |
| V-6 | `alg:dccd` 出現箇所 | §4c L282 (定義) + §10b L12 ref; alg:dccd_adv は別 label |
| V-7 | `sec:level_selection` 出現箇所 | §10_3 L7 (定義) + 10 ref (集約成功) |
| V-8 | `Warning.*undef` 件数 | 0 (xelatex log) |

## 6. Lessons Learned (KL-10)

- **KL-10-1**: 構造リファクタは内容修正と分離して独立 task 化すべき．CHK-205..213 が 9 passes で内容 saturation を達成した後にこそ，全体構造を客観的に再評価できた．混在させると review pass ごとに焦点がぶれる．
- **KL-10-2**: phantomsection / in-place label retention 戦略により，大規模 cross-ref 移動の break リスクを最小化できる．本 task では 12 件の deviation 移動で V-1..V-7 全件 protection を確認．Phase 8 で 1 件発生した重複 label も最小修正で解消．
- **KL-10-3**: Part 構造の厳格化は **section level の reorganization** で達成可能であり，新規 chapter file の作成は不要．既存 file 内 subsection 追加と pointer paragraph で吸収できる．

## 7. Out of Scope (引き継ぎ)

- **CHK-216 (今後)**: §13 動力学検証の完成 (Hysing terminal velocity / RT mode growth rate / Capillary wave dispersion 等の実験実行依存タスク)
- **CHK-216 (今後)**: §11 Step 5/7 単体検証追加
- **main へのマージ**: Phase 完了後にユーザ確認待ち; 本 worktree (`worktree-ra-paper-restructure-part123`) はまだ独立 branch

## 8. Commit 一覧

| # | Commit | Phase | 内容 |
|---|---|---|---|
| 1 | c8f70fe | Phase 1 | §10b Bootstrap → 付録 H ref (γ-3) |
| 2 | b2e100a | Phase 2 | §3 → §6/§7 deviation 移動 (α-3, α-4, α-5) |
| 3 | fcebd54 | Phase 3 | §1 Glossary/技術要素一覧 → §4 冒頭 (α-1, α-2) |
| 4 | b63ddfb | Phase 4 | Level routing → §10_3 集約 (β-1..β-4) |
| 5 | 82e6994 | Phase 5 | §10b DCCD パラメタ → §4c (γ-1, γ-2) |
| 6 | cc58ff0 | Phase 6 | §10_5 Phase 2/3 詳述 → §7c/§7e ref に圧縮 (γ-4) |
| 7 | 250cb9f | Phase 7 | §13 浮力分解再掲削除 + §1b roadmap 同期 (γ-5) |
| 8 | 82ab8ce | Phase 8 | sec:dc_pure_fccd_convergence 重複 label 解消 (build verify) |
| 9 | (next) | Phase 9 | LEDGER 更新 + 本メモ追加 |

**Net LOC**: ≈ +0 (移動主体); 削除 49 (γ-3 Bootstrap) + 圧縮 10 (γ-5 浮力分解) で純減 ~59 LOC，新設 subsection (sec:notation_glossary / sec:tech_roadmap / sec:dccd_params / sec:dc_pure_fccd_convergence / sec:level_gpu_dual_path) で純増 ~60 LOC．
