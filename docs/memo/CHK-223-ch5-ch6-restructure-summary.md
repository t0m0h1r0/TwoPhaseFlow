# CHK-223 — §5/§6 構造再編 (CLS-specific / per-term spatial / time integration)

**Date**: 2026-04-26
**Branch**: `worktree-ra-paper-ch4-rewrite`
**Trigger**: CHK-222 完了後ユーザより 4 件構造的懸念
**Result**: §5 NEW (CLS-specific) → §6 NEW (per-term spatial) → §7 NEW (time integration) の 3 章分離; xelatex 257 pp clean; V-1..V-10 全 pass

---

## 背景: CHK-222 後の追加査読 4 件懸念

| # | 懸念 | 根本原因 |
|---|---|---|
| 1 | §5 (時間積分) → §6 (CLS 離散化) の章順序が逆 | §5.3 で TVD-RK3 ψ^{n+1} 更新を書いているが FCCD 空間演算子は §6 で初めて定義 (forward ref `\ref{sec:advection}`) |
| 2 | 時間積分の話が §6 (CLS 離散化章) に混入 5 件 | 07d Stage A TVD-RK3 重複 / 07d sec:cls_velocity_consistency / 07b warn:cls_dtau_stability / 07b sec:stability / 07e sec:viscous_cn_defect |
| 3 | §5 で「ρ, μ に CCD 適用は不適切」と書かれているが対処方法が不在 | 禁止規範は 07_0 L48-51 のみ; 規範式は 07e L113-119 に分散; 読者は §5 を読んだだけでは ρ/μ 評価方法を知ることができない |
| 4 | §6.5 viscous は CLS 文脈から逸脱 | 07e ~85% は変粘性 NS 粘性項離散化 (Layer A/B/C) で CLS 非依存 |

共通根: **章境界の論理的順序が乱れている** (時間/空間/CLS 文脈の三相が混在).

---

## ユーザ確定設計判断

- **Q1 = (D) 全面再構成 + 順序: §5 NEW (CLS-specific) → §6 NEW (per-term spatial) → §7 NEW (time integration)**
  - 理由 1: 空間 → 時間は連続のほうが理解しやすい (§6 → §7 連続接続)
  - 理由 2: 空間の話の中で LS/CLS 文脈 (ρ=ρ(ψ) 等) を前提にする必要があるため CLS-specific を先に置く
- **Q2 = 新空間章 §6 NEW で ρ/μ 規範を確立**
  - prohibition + concrete formulas を co-locate
  - 時間積分章 §7 NEW は §6 NEW 参照のみ

---

## 新章構成 (CHK-223 後)

| 章 | 内容 | 主ファイル |
|---|---|---|
| §3 | LS/CLS theory | `03_*.tex` (unchanged) |
| §4 | CCD/FCCD/UCCD6 operators | `04_*.tex` (unchanged) |
| **§5 NEW** | **CLS 専用アルゴリズム** (Ridge-Eikonal + A-F 6 stages + ψ↔φ mapping) | `07b_reinitialization` + `07d_cls_stages` |
| **§6 NEW** | **方程式項別空間離散化** (CLS ψ FCCD + 運動量 FCCD/UCCD6 + 粘性 Layer A/B/C + ρ/μ 補間規則) | `07_0`, `07_advection`, `07c`, `07e` |
| **§7 NEW** | **時間積分** (旧 §5 + 移行 5 件) | `05_time_integration.tex` |
| §8+ | PPE / collocate / BF / CCD Poisson / Non-uniform / Algorithm / Verification / Conclusion | (番号 +1 シフト) |

論理的な流れ: §3 (連続 LS/CLS) → §4 (operator) → **§5 (CLS algorithmic framework)** → **§6 (CLS context を前提とした per-term spatial)** → **§7 (空間直後の時間積分)** → §8+ (補助). §6 → §7 が連続することで「空間 → 時間」の認知負荷が最小化される.

---

## 7 段階実行と成果

### Phase 1: §5 NEW + §6 NEW chapter intros 新設

- `07b_reinitialization.tex` 冒頭に `\section{CLS 専用アルゴリズム}` + `\label{ch:cls_specific}` + chapter intro 段落
- `07_0_scheme_per_variable.tex` を `\subsection` → `\section{方程式項別空間離散化}` 昇格 + `\label{ch:per_term_spatial}`
- 設計原則第 6 番目「ρ, μ は §6.4 corner μ 補間規則で評価」追加

### Phase 2: main.tex chapter ordering 変更

- 旧: `05_time_integration` → `07_0` → `07_advection` → `07c` → `07b` → `07d` → `07e`
- 新: `07b` → `07d` (§5 NEW) → `07_0` → `07_advection` → `07c` → `07e` (§6 NEW) → `05_time_integration` (§7 NEW)
- `\label{ch:time_integration}` + backward-compat `\label{sec:time_int}` を §7 冒頭に追加

### Phase 3: §5 NEW + §6 NEW から時間積分内容 5 件抽出

- 07d Stage A TVD-RK3 (L79-90): §7.3 ref に圧縮 + `phantomsection eq:cls_rk3_{1,2,3}` alias 残置
- 07d sec:cls_velocity_consistency (L128-143): 5 行 redirect; 旧 alias は §7 destination に移転
- 07b warn:cls_dtau_stability (L407-432) + sec:stability (L443-490): 80 LOC 削除
- 07e sec:viscous_cn_defect (L185-222): 40 LOC 削除
- 一時 stage file `/tmp/migrate_*.tex` 4 件作成 (Phase 4 統合用)

### Phase 4: §7 NEW (time integration) に 5 件統合

- `\subsubsection{速度--PPE 整合性}` (`sec:cls_velocity_consistency_v7` + alias `sec:cls_velocity_consistency`) を warn:tvd_rk3_scope 直後に挿入
- `\subsubsection{Crank--Nicolson 粘性 Helmholtz とデフェクト補正}` (`sec:viscous_cn_defect_v7` + alias `sec:viscous_cn_defect` + `eq:viscous_cn_helmholtz` + `eq:viscous_cn_helmholtz_v7`) を §7.4 末尾に追加
- `\subsubsection{CLS 再初期化の擬似時間}` (`warn:cls_dtau_stability_v7` + alias `warn:cls_dtau_stability`) を §7.9 sec:time_guide に追加
- `eq:dt_adv` + `eq:dt_sigma` を §7.9 sec:time_guide に full-labeled equation として復活 (§12+/§13_* refs 保護)

### Phase 5: 章番号 ripple

- 全 `\ref{}`-based ref は LaTeX 自動更新 (副作用なし)
- sec: alias 整備: `sec:advection` / `sec:fccd_advection` / `sec:cls_compression` / `sec:viscous_3layer` / `sec:cls_stages` / `sec:time_int` 等は phantomsection 保持
- 14 phantomsection alias 配置 (3 × 07d + 3 × 07b + 2 × 07_advection + 6 × 05_time_integration)

### Phase 6: ρ/μ prescription §6.4 NEW co-location (Q2 確定)

- 07e 末尾に `\subsection{ρ, μ 物性値補間規則}` + `\label{sec:rho_mu_interpolation}` 新設
- 5 subsubsection 構成:
  - `sec:rho_mu_cell_center`: cell-center 代数更新 (`eq:rho_update`, `eq:mu_update`)
  - `sec:mu_face_interpolation`: face μ arith vs harm tradeoff (`eq:mu_face_arith`, `eq:mu_face_harm`)
  - `sec:mu_corner_interpolation`: corner μ §6.3 ref
  - `sec:rho_mu_time_integration`: ordering (Stage F → ρ/μ update → predictor)
  - `sec:rho_mu_failure_modes`: 4 件 (CCD 直接 / 算術平均 高粘性比 / τ_xy 別計算 / クランプ前更新)
- 07d/07e/07c file-header コメント更新 (§6.5/§6.6/§6.3 → §5.2/§6.3/§6.2)

### Phase 7: V-grep + LEDGER + memo + commits

- V-1..V-10 全 pass (詳細は本 memo §V-grep 結果)
- xelatex 2-pass clean 257 pp; 0 LaTeX warnings; 0 multiply-defined; 0 undefined refs

---

## V-grep 結果 (V-1..V-10)

| V# | 検証項目 | 結果 |
|---|---|---|
| V-1 | §5/§6/§7 章タイトル順序 = 「CLS-specific / per-term spatial / time integration」 | ✓ pass |
| V-2 | §6 NEW 内 ρ/μ prescription co-located | ✓ pass (`sec:rho_mu_interpolation` + 5 eq labels in 07e) |
| V-3 | §5 NEW + §6 NEW から時間積分内容 5 件全て削除 | ✓ pass (Stage A TVD-RK3 ref-only / cls_velocity_consistency 圧縮 / dtau+stability+cn_defect 削除) |
| V-4 | §7 内に移行内容 5 件全て統合 | ✓ pass (sec:cls_velocity_consistency_v7 + sec:viscous_cn_defect_v7 + warn:cls_dtau_stability_v7 + eq:dt_adv + eq:dt_sigma) |
| V-5 | forward ref 完全消滅 | ✓ pass (旧 §5 → §6 forward ref が §7 → §6 backward ref に転換; sec:advection ref 1 件は § §6 → §7 順序で正常解決) |
| V-6 | backward-compat alias 確認 | ✓ pass (14 phantomsection alias 適切配置) |
| V-7 | 章番号 hard-coded narrative text 整合 | ✓ pass (新 §5/§6/§7 + §7.x が narrative の主成分; 旧 §5.5/§5.6/§5.9/§6.5/§6.6 はすべてコメント or alias 内) |
| V-8 | §3/§4 への ref 健全 | ✓ pass (sec:CCD/sec:fccd_def/sec:uccd6_def/sec:cls_advection 等全 resolve) |
| V-9 | §8-§14 への ref 健全 | ✓ pass (sec:val_capillary/sec:val_summary/sec:balanced_force/sec:algorithm/sec:collocate_layout 全 resolve) |
| V-10 | xelatex 2-pass 0 undef | ✓ pass (257 pp / 0 multiply-defined / 0 undefined / 0 LaTeX warnings) |

---

## KL 系 (CHK-223 で確立)

### KL-18-1: 「CLS-specific / per-term spatial / time integration」3 章分離の judging criterion

CLS-specific 章 (§5 NEW) と per-term spatial 章 (§6 NEW) の境界は以下のように峻別:

- **§5 NEW (CLS-specific)** = アルゴリズム orchestration: 再初期化, 6 段階 (Stage A-F の責務分離), ψ↔φ mapping (tanh/artanh ペア)
- **§6 NEW (per-term spatial)** = operator と方程式項のマッピング: どの operator (CCD/FCCD/UCCD6/低次/2 次中心) を どの方程式項 (CLS ψ 移流 / 運動量 / 粘性 / 物性値 / 圧力 jump) に使うか

判定例:
- CLS ψ FCCD 移流の operator 自体は §6.1 NEW (per-term spatial)
- CLS 6 段階内での Stage A/B/F の責務 (mass / geometry / correction) は §5.2 NEW (CLS-specific)
- ρ=ρ(ψ) 線形内挿は §6.4 NEW (per-term spatial で operator-of-choice として位置付け)
- ψ↔φ tanh/artanh mapping は §5.2 NEW (CLS framework 固有のアルゴリズム)

CLS context を spatial の前提として配置する設計原則:
**ρ, μ の代数更新は CLS context (ψ ∈ [0,1]) の前提 → §5 で CLS context 確立後に §6 で operator 選択原則を述べる**.

### KL-18-2: ρ/μ prescription co-location 設計 — 禁止 + 規範式の co-located vs distributed

旧構成 (CHK-222 まで): 禁止規範 (07_0) と規範式 (07e corner μ) が分散していた → 読者は「禁止」を §5 で読んだあと「対処方法」を §6 まで探す必要があった.

新構成 (CHK-223): §6.4 NEW 単独 subsection で co-locate:
1. **設計動機** (なぜ低次代数更新か; Gibbs 振動回避)
2. **cell-center ρ, μ** (eq:rho_update, eq:mu_update; CLS Stage F 後)
3. **face μ** (arith vs harm tradeoff; 高粘性比は調和平均)
4. **corner μ** (§6.3 ref; 4 点平均)
5. **time integration ordering** (Stage F → ρ/μ update → predictor)
6. **failure modes** (4 件)

時間積分章 §7 NEW は `\ref{sec:rho_mu_interpolation}` 1 行参照のみで完結.

設計原則: **prescription は規範のみで完結する subsection に co-locate**; reference は単方向 (§7 → §6.4) で双方向 ref を作らない.

### KL-18-3: 章番号 ripple 管理 — label-based ref 優先 vs hard-coded "§N" narrative

`\ref{}` ベース参照は LaTeX が自動更新する (Phase 5 で全件 resolve 確認).
hard-coded "§N で" narrative は手動 grep & replace 必須.

CHK-223 では §5 NEW / §6 NEW / §7 NEW の章ラベル `ch:cls_specific` / `ch:per_term_spatial` / `ch:time_integration` を新設し,既存 `\ref{ch:advection}` 等の旧 chapter alias も `\phantomsection\label{}` で保護.

外部参照 (§10_full / §11f / §appendix_ppe_pseudotime / §08b 等) は全て `\ref{}` ベースなので章番号 ripple の影響なし.

教訓: **新章の `ch:xxx` label は最初から確定的に命名し,後段からの ref を全て label-based で書く**; "§7 を参照" のような hard-coded narrative は最終 chapter ordering 確定後に grep & replace.

### KL-18-4: 「空間 → 時間 連続接続」設計原則 — §6 (per-term spatial) → §7 (time integration) の認知負荷最小化

旧構成 (CHK-222 まで): §5 (時間積分) → §6 (CLS 離散化) → §7 (PPE) の順序は時間 → 空間 → 空間 (PPE) で「空間と時間が混在」する認知負荷が高い構造だった.

新構成 (CHK-223): §5 (CLS-specific) → §6 (per-term spatial) → §7 (time integration) → §8+ (補助) は CLS context → 空間 → 時間 → 補助の連続接続で,読者は線形的に学習できる.

設計原則: **空間と時間は隣接させる**; 空間 (per-term operator 選択) を述べた直後に時間 (operator splitting / IMEX / CN) を述べることで「どの operator がどの time-stepping form に入るか」が直接ハンドオフできる.

具体的なハンドオフ例:
- §6.1 (CLS ψ FCCD 移流) → §7.3 (TVD-RK3 ψ^{n+1} 更新): 空間 operator → time-stepping
- §6.3 (粘性 Layer A/B/C) → §7.4 (CN Helmholtz + defect): 空間 operator → 半陰的処理
- §6.4 (ρ/μ 補間規則) → §7.3 (Stage F → ρ/μ update → predictor): 物性値 → 時間 ordering

---

## 残課題 (CHK-224 候補)

- ch13 検証章への measurements 実書込み (CHK-222 から継続)
- main マージ判断待ち (CHK-221/222/223 まとめてマージ可能)
- §5 NEW / §6 NEW / §7 NEW 内部の小節順序最適化 (Phase 8 候補; ch13 production stack の measurements が ch13 に書き込まれた後に再検討)

---

## 参考: CHK-222 → CHK-223 の差分要約

| 観点 | CHK-222 終状 | CHK-223 終状 |
|---|---|---|
| 章数 | §5 (時間積分) + §6 (CLS 離散化) の 2 章; §6.5/§6.6 が時間積分内容混在 | §5 NEW (CLS-specific) + §6 NEW (per-term spatial) + §7 NEW (time integration) の 3 章 |
| ρ/μ 規範 | 07_0 (禁止) + 07e (corner μ 規範式) に分散 | §6.4 NEW (`sec:rho_mu_interpolation`) で co-located; §7 は 1 行 ref |
| forward ref | §5 → §6 forward ref 1 件 (sec:advection) | §6 → §7 順序で全 backward ref 化 |
| 時間積分混入 | §6 内に 5 件混入 | 全件 §7 NEW へ移行 + alias 配置 |
| pp | 256 | 257 (+1; 純内容追加 §6.4 NEW) |
| xelatex | 2-pass clean | 2-pass clean (0 multiply / 0 undef / 0 warn) |
