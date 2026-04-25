# CHK-220 — §5 (時間積分章) 査読官レビュー + per-term 再編 + ch13 production stack 整合

**Date**: 2026-04-26
**Branch**: worktree-ra-paper-ch4-rewrite
**Phase**: PAPER_CH5_REVIEW
**Status**: DONE (V-1..V-7 全 pass; xelatex clean 259 pp)

---

## 1. Trigger

ユーザ指摘 (CHK-219 §6 review main マージ後の追加要請):

> 5 章の時間積分スキームについて、査読官になったつもりで厳正にレビューを行って。以下が気になっている
>
> * `ch13/**/*yaml` の実験で使っているスキームと異なるものが重点的に説明されている。使われているものを優先したい
> * レベル分けにはあまり意味がない。それよりも各項 (移流・粘性・界面張力 等) で使うべきスキームは何か・なぜかを重点的に説明すべき
> * 時間積分の安定性への説明・言及が重要

## 2. 探索結果と決定

### 2.1 §5 構造マップ (CHK-220 開始時; 656 LOC)

| 章番号 | label | LOC | 内容 |
|---|---|---|---|
| §5 章ヘッダ + intro | sec:time_int | 32 | Level 1/2/3 enumerate + ロードマップ |
| §5.1 | sec:time_accuracy_principle | 52 | 精度整合性原則 + Level スペクトル比較表 |
| §5.2 | sec:time_operator_stiffness | 30 | 演算子別剛性マップ表 |
| §5.3 | sec:time_level1 | 46 | Level 1: SSPRK3 (CLS 移流専用) |
| §5.4 | sec:time_level2 | 350 | Level 2: AB2/IMEX-BDF2 + IPC + CN |
| §5.4.1 | sec:ipc_derivation | 43 | IPC δp 求解 |
| §5.4.2 | sec:time_accuracy_table | 80 | Level 2 全体時間精度表 |
| §5.4.3 | sec:time_cn | 115 | Crank-Nicolson 法 (対角粘性項) |
| §5.5 | sec:time_level3 | 39 | Level 3: Radau IIA (実装ゼロ) |
| §5.6 | sec:time_capillary | 50 | 毛管波時間刻み制約 (BKZ + Denner) |
| §5.7 | sec:time_guide | 42 | 時間刻みガイド (Level 別律速合成) |

### 2.2 ch13 production stack (`experiment/ch13/config/*.yaml`)

| 物理項 | 時間積分 | 空間 |
|---|---|---|
| 界面 (CLS) | tvd_rk3 | fccd |
| NS 対流 | imex_bdf2 (EXT2 外挿) | uccd6 |
| 粘性 | implicit_bdf2 (GMRES) | ccd |
| 界面張力 | pressure_jump (PPE 内蔵 jump_decomposition) | — |
| 圧力 | IPC + FCCD PPE (defect_correction + phase_separated) | fccd |
| 浮力 (rising bubble) | balanced_buoyancy (explicit) | — |
| CFL | run.time.cfl=0.10 | — |

### 2.3 主要乖離 (5 件)

1. §5.4 主定式 (eq:predictor_ab2_ipc) は AB2+IPC+CN だが ch13 は IMEX-BDF2 + implicit_bdf2 を採用
2. §5.4.3 CN 法 ~115 LOC は ch13 不使用 (implicit_bdf2 GMRES)
3. §5 に pressure_jump (PPE 内蔵) の時間精度議論ほぼなし
4. Level 1/2/3 概念は YAML/src/ 両方に存在しない
5. §5.3 L139 CLS 移流の空間スキームを「DCCD」と記述 (ch13 は FCCD)

### 2.4 安定性記述の現状 (薄い)

| 安定性 | 状態 |
|---|---|
| BKZ 毛管波 (§5.6 ~49 LOC) | 詳述 |
| 変粘性クロス CFL (warn:cross_cfl) | 詳述 |
| CN A-stable / AB2 零安定性 / IRK4 A/L-stable | 各 1 行のみ |
| Strang split 整合性 / Brunt-Väisälä / CN \|G(θ)\|² / GMRES 収束性 | **記述なし** |

### 2.5 ユーザ決定事項 (AskUserQuestion 経由)

1. **§5 章構造**: 完全削除 + per-term 再編 (Option A; radical)
2. **CN 法**: legacy paragraph に縮減 (~50 LOC)
3. **浮力**: 新規節 §5.7 として追加 (~35 LOC)

## 3. 新章構造 (実装後; 841 LOC)

```
§5 時間積分スキーム — 項別設計と ch13 production stack
\label{sec:time_int}                              (12+ 件外部参照保護)
├── intro: Part 1 inheritance ブロック + ch13 項別配分表 + per-term ロードマップ
├── §5.1 精度整合性の原則 (sec:time_accuracy_principle)        ~30 LOC
├── §5.2 演算子別剛性マップ (sec:time_operator_stiffness)      ~35 LOC
│   + Strang split 整合性注記
├── §5.3 移流項：CLS 用 TVD-RK3 + NS 用 IMEX-BDF2              ~80 LOC
│   \phantomsection\label{sec:time_level1}                    (10_3 ref 保護)
│   ├ CLS 移流 (TVD-RK3 + FCCD; ch13 主実装) — DCCD→FCCD 訂正
│   ├ NS 対流 (IMEX-BDF2 EXT2 + UCCD6; ch13 主実装)
│   ├ 安定性: 対流 CFL + AB2 vs IMEX-BDF2 安定領域比較
│   └ legacy: 旧 AB2+IPC 定式 + warn:ab2_startup
│       \phantomsection\label{sec:ab2_ipc} (6 件保護)
├── §5.4 粘性項：implicit-BDF2 (GMRES)                         ~95 LOC
│   ├ 主定式 (Helmholtz 形 (I − γΔt L_ν)u* = RHS, γ=2/3)
│   ├ GMRES 収束性 + Jacobi 前処理 + restart 80 / ~500 iter
│   ├ 安定性: A-stable + 粘性 CFL 消滅
│   ├ クロス項処理 (warn:cn_cross_derivative + warn:cross_cfl 維持)
│   └ legacy: 旧 CN 主定式 ~50 LOC
│       \phantomsection\label{sec:time_cn} (3 件保護)
├── §5.5 界面張力項：PPE 内蔵 jump-decomposed CSF (sec:time_csf) ~80 LOC
│   ├ jump_decomposition 時間精度 (eq:pressure_jump_csf, eq:ppe_jump_decomposed)
│   ├ rem:implicit_csf_capillary (陰的化と毛管波物理解像の独立性)
│   ├ 陽的 CSF (legacy) との比較
│   └ 毛管波制約 subsubsection (BKZ + Denner-vW)
│       \phantomsection\label{sec:time_capillary} (2 件保護)
├── §5.6 圧力投影：IPC + FCCD PPE (sec:ipc_derivation)          ~50 LOC
│   ├ δp 導出 (Chorin → IPC; O(Δt) → O(Δt²))
│   ├ FCCD PPE と defect-correction の役割
│   └ 安定性: 投影演算子の射影性
├── §5.7 浮力項：balanced_buoyancy (sec:time_buoyancy)          ~35 LOC
│   ├ hydrostatic/residual 分離 (eq:buoy_split, eq:buoy_residual)
│   ├ 寄生流 (parasitic flow) 抑制原理 (BKZ 1992)
│   ├ Brunt-Väisälä 周波数 (eq:brunt_vaisala) + 浮力波制約
│   └ warn:balanced_buoy_scope (rising bubble 限定)
├── §5.8 全体時間精度 (sec:time_accuracy_table; 8 件保護)       ~50 LOC
│   tab:time_accuracy_prod — 3 stream (ch13 prod / legacy / 時間精度) × 7 物理項
├── §5.9 時間刻みガイド (sec:time_guide)                       ~30 LOC
│   eq:dt_per_term Δt_ch13 = min(Δt_adv, Δt_cap, Δt_buoy, Δt_operator)
└── §5.10 補足：他 Level 設定 (sec:time_level_legacy)           ~15 LOC
    \phantomsection\label{sec:time_level3}                    (10_3 ref 保護)
    Level 1 (SSPRK3) = 検証用 / Level 3 (Radau IIA) = 設計フック (実装なし)
```

**LOC 推移**: 656 → 713 (Phase 1-3) → 779 (Phase 4) → 862 (Phase 5) → 841 (Phase 6); 純増 +185 LOC (per-term 再編 + 新規節 §5.5/§5.7 + GMRES 詳述による).

## 4. Phase 別内訳 (7 phase / 6 paper commit + 1 ledger/memo commit)

| # | Commit | 主内容 | LOC 変化 |
|---|---|---|---|
| 1 | a4e87bd | 章ヘッダ + Part 1 inheritance + ch13 配分表 + §5.1/§5.2 改訂 | +18 |
| 2 | 99e62fe | §5.3 移流項 IMEX-BDF2 主軸化 + DCCD→FCCD + AB2+IPC legacy 化 | +45 |
| 3 | 51c9590 | §5.4 粘性項 implicit-BDF2 (GMRES) 主軸化 + CN legacy 縮減 | -6 |
| 4 | bdb174a | §5.5 界面張力 PPE 内蔵 jump-decomposed CSF 新規 + 旧 §5.6 統合 | +66 |
| 5 | e61afc0 | §5.6 IPC 独立節昇格 + §5.7 浮力 balanced_buoyancy 新規執筆 | +83 |
| 6 | 318503b | §5.8/§5.9/§5.10 + 大規模 section 移動 + §10_3 同調 | -21 |
| 7 | (本 commit) | LEDGER CHK-220 + memo (KL-15) | (paper 0; doc only) |

## 5. V-grep 検証結果 (Phase 7)

| # | 検証 | 結果 |
|---|---|---|
| V-1 | `\subsection` 件数 = 9-10 | **10** ✓ |
| V-2 | Level 1/2/3 主本文記述ゼロ | §5.10 補足 + phantomsection + legacy 限定 ✓ |
| V-3 | 全外部参照 phantomsection 解決 | sec:time_level1/2/3 + sec:ab2_ipc + sec:time_cn + sec:time_capillary 全件 ✓ |
| V-4 | DCCD は §5.3 legacy footnote/§4 ref のみ | 主本文 0 件 ✓ |
| V-5 | IMEX-BDF2/implicit-BDF2/pressure-jump/jump-decomposed/balanced-buoy/Brunt-Väisälä/GMRES 各 1 件以上 | 7 keyword 全件 §5.3-§5.7 出現 ✓ |
| V-6 | Part 1 inheritance refs (sec:onefluid/cls_advection/reinit/CCD) ≥4 件 | ✓ |
| V-7 | latexmk -xelatex clean | 0 undef refs / 0 multiply defined; 259 pp (target 257±5 内) ✓ |

## 6. KL-15 抽出 (Lessons Learned)

### KL-15-1: narrative axis 転換 (縦軸 Level → 横軸 per-term) の commit cost

章構造軸の根本変更は 7 phase 構成で安全に遂行可能．Phase 1 で章タイトル + intro を先に変更することで読者の認知 frame を切り替え，Phase 2-5 で各 per-term 節を独立に書換える戦略が有効．CHK-219 (§6 review) の per-term 化と同じパターンであり，**「章タイトル先行 → 各物理項節を独立 commit」の 2-stage approach** が論文章構造の根本変更の安全な手順として確立．

### KL-15-2: phantomsection による「概念名 label」の保護

削除した概念 (Level 1/2/3) の label を新章構造の「補足節」(§5.10 sec:time_level_legacy) に集約して `\phantomsection\label{}` で保持することで外部章 (10_3) との互換維持．**「概念削除」と「label 維持」を独立に管理可能**．本 CHK では:

- `sec:time_level1` → §5.3 header 直下 (旧 Level 1 = CLS 用 TVD-RK3 と framing 整合)
- `sec:time_level2` → §5.3 内 AB2+IPC legacy paragraph (旧 Level 2a と framing 整合)
- `sec:time_level3` → §5.10 (Radau IIA 設計フック; 実装ゼロ)
- `sec:ab2_ipc` (6 件) / `sec:time_cn` (3 件) / `sec:time_capillary` (2 件) — それぞれ legacy paragraph または subsubsection に設置

CHK-218 の `sec:fccd_nonuniform_sketch` 移動 + CHK-219 の `sec:cls_on_nonuniform` 移動と同パターン (累積 KL: 大規模 cross-ref 移動の break リスク最小化技法).

### KL-15-3: 新規節執筆 (pressure_jump / GMRES / Brunt-Väisälä) の典型構成

実装側 (src/twophase/) で確立しているが論文側で未記述の topic を埋める Phase の典型 LOC 配分:

| 部位 | LOC | 例 |
|---|---|---|
| 主定式 | ~5 | Helmholtz 形 / hydrostatic 分離 / [∇p·n̂]_Γ = σκδ_Γ |
| 数値特性 | ~15-20 | GMRES 収束性 / 寄生流抑制原理 / splitting error 比較 |
| 安定性 | ~5-10 | A-stable / 浮力波制約 Δt ≲ N_BV⁻¹ |
| resultbox/warnbox | 1-2 件 | 収束目安表 / scope 限定 warning |

§5.4 (GMRES) ~25 LOC + §5.5 (jump-decomposed CSF) ~30 LOC + §5.7 (浮力 balanced_buoyancy) ~35 LOC が本 typical template に収束．

### KL-15-4: 安定性議論の per-term 配置

各 per-term 節末尾に対応する安定性議論を置く構成は，読者が「項別の物理時間スケール」を把握しやすくなる．本 CHK での配置:

- §5.3 末尾 → 対流 CFL + AB2 零安定 vs IMEX-BDF2 BDF2 component A(α)-stable
- §5.4 末尾 → A-stable (implicit-BDF2) + GMRES 収束性
- §5.5 末尾 → BKZ 毛管波 + Denner-vW 波解像制約
- §5.7 末尾 → Brunt-Väisälä N_BV (浮力波)

旧 §5.6 (毛管波制約) を独立節として配置していた構成と比較し，**per-term 設計と安定性が直接結びつく利点**．§5.9 律速合成式 Δt = min(Δt_adv, Δt_cap, Δt_buoy, Δt_operator) との整合も取れる．

## 7. 残課題と Out-of-scope

### 残課題

- main マージはユーザ判断待ち (本 worktree 継続使用)
- 旧 CN 法 §11f sec:verify_cn_viscous の検証実験節は CN legacy 化と矛盾しないため変更なし (検証データは保持)

### Out-of-scope (CHK-220 では扱わない)

- DCCD 関連 src/ コード削除 (CHK-219 と同様 src/ 残存; 互換テスト用)
- §10_full_algorithm.tex の AB2+IPC narrative 大規模更新 (現 CHK では §10_3 最小同調のみ; §10 主体 narrative は別 CHK で対処)
- ch13 YAML key 名 (imex_bdf2 / implicit_bdf2 / pressure_jump / balanced_buoyancy) の §5 本文への直接引用 — PROD 名称は §10 アルゴリズム章に集約; §5 は概念名 (IMEX-BDF2 / implicit BDF2 / PPE 内蔵 jump-decomposed CSF / balanced 浮力) のみ使用
- 数値検証実行・新規実験追加なし

## 8. 関連 CHK / 累積 KL

- **CHK-219** (prev): §6 (移流章) per-term 化 — 本 CHK の章構造変更パターンの prior art
- **CHK-218**: §6 章移動 + forward-ref 整合 — phantomsection による label 保護パターンの prior art
- **CHK-216/217**: §4 (CCD 章) 抜本改稿 + 査読 review — narrative purification と review 分離 task 化の prior art

累積 lessons:

- **章構造軸の根本変更は 7 phase 構成で安全** (CHK-216 + CHK-219 + CHK-220 で実証)
- **phantomsection は「概念削除と label 維持の独立管理」を可能にする標準技法** (CHK-218 + CHK-219 + CHK-220 累積)
- **論文書換は実装側 (ch13 production) の確立後に行うべき** (CHK-219 KL-14-1 累積; 本 CHK で再確認)

---

**End of CHK-220 summary**
