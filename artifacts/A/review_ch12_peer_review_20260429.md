# Peer Review: Chapter 12 「数値要素の単体検証実験」

**CHK**: CHK-RA-CH12PR-001
**Reviewer role**: journal reviewer (single-blind, 厳正)
**Review date**: 2026-04-29
**Branch**: `worktree-ra-ch12-peer-review-20260429`
**Review scope**: Chapter 12 paper sources (`paper/sections/12*.tex`, 11 files / 1251 行) + 該当する experiment スクリプト (`experiment/ch12/exp_U[1-9]_*.py`, 9 files / 2803 行) + 該当する production source (`src/twophase/{ccd,levelset,ppe,hfe,time_integration}/...`)

---

## 0. TL;DR (Summary verdict)

> **Recommendation**: **Major Revision** required before acceptance.

**Strengths.**
1. 単体検証 9 ユニット (U1–U9) を Tier I–VII の階層付けで体系化。Algorithm Fidelity (PR-5) を「ピース毎」に切り出して検証する、論文後半 (Ch 13/14) のシステム検証への土台として **構造が明快**。
2. 大半の slope 結果 (U1-a CCD 6.00, U2-a Dirichlet k=3 6.90, U7-b face-μ 1.91, U8-a TVD-RK3 3.00) は理論次数を機械精度域までクリーンに到達しており、**コア CCD/PPE 部の実装健全性**は十分担保されている。
3. U9 (DCCD on pressure 禁止) の **negation test** は設計規則 (PR-5) を定量化する稀有な試みで、論文全体の design rationale を強化している。

**Critical concerns.**
1. **[Fatal] アルゴリズム同一性の破綻**: 以下のテストは「論文が主張するアルゴリズム」を実際には検証していない。
   - **U4 (再初期化)**: 論文セクションタイトル「Ridge Eikonal 再初期化」の主張に反し、production の `RidgeEikonalReinitializer` は単発 FMM ベースで `n_τ` 反復を持たないため **byPass され、`godunov_sweep` 直叩き**になっている (`exp_U4_ridge_eikonal_reinit.py:17-21` の docstring が自認)。
   - **U8-c (CN-ADI)**: 論文 §12.U8 は「CN--ADI (Peaceman--Rachford)」と明示するが、script は `_cn_diffusion_2d_error` で **FFT 対角化のスペクトル CN** を実装しており ADI 分割は **皆無** (`exp_U8_time_integration_suite.py:102-126`)。production の `cn_diffusion_axis` (Thomas tridiagonal) も呼ばれていない。
   - **U8 全体**: TVD-RK3 / AB2 / CN いずれも **inline 再実装**。production の `twophase.time_integration` モジュールから **import 0 件** (`exp_U8_time_integration_suite.py:38-42`)。
   - **U2 (PPE BC)**: 論文は production の PPE solver (Defect Correction; `PPESolverCCDLU`/`PPESolverFCCDMatrixFree`) の検証を含意するが、script は `fd_laplacian_dirichlet_2d` + `sparse_solve_2d` ヘルパーで **手作り**、DC iteration は inline ループ (`exp_U2_ccd_poisson_ppe_bc.py:40-43, 87-92`)。
   - **U3 (非一様格子)**: 論文 §12.U3 setup は「界面 x = 0.5 (planar)」と明記するが script は `phi = (X − 0.5) + (Y − 0.5)` の **45° 対角線** を界面とする (`exp_U3_nonuniform_spatial_suite.py:104`)。

2. **[Major] 数値・記号の表内不整合**:
   - tab:U6_dc_omega: 本文宣言 `ω ∈ {0.2, 0.3, 0.5, 0.7, 0.9}` (5 個) ↔ 表掲載 (3 個) ↔ script 実行 `[0.2, 0.3, 0.5, 0.7]` (4 個) の **三方齟齬**。
   - tab:U6_dc_omega: ρ_l=1 行が caption で言及されながら **表本体に欠落**。
   - tab:U_summary (parent) で U9 が ●、tab:verification_summary (summary) で U9 が ✓ — **同章内で記号体系が不統一**。
   - tab:U9_dccd_violation: ε_d=0.25 の ratio 列が表にあるべきだが **欠落**。
   - U9 spectral filter formula: 本文 §12.U9 line 73 で `H(ξ; ε_d) = 1 − 4ε_d sin⁴(ξ/2)`、しかし U1-b および script (`_filter_1d_periodic`) は `1 − 4ε_d sin²(ξ/2)`。**§U9 の式が誤** (sin² が正)。
   - U2 setup: 「2D 周期領域」と書くが用いる MMS は `sin(πx) sin(πy)` (Dirichlet)。**境界条件記述と MMS が不整合**。

3. **[Major] 判定基準の逸脱**:
   - U6-c HFE 2D 中央値 slope **3.21** (設計 6) を **△** で通している (line ≈ 5.10 max は近いが、median 2.79 は許容帯 ±0.5 を逸脱)。これは事実上 ✗ で、**判定甘さ**。
   - tab:verification_summary の U5-a を「1 次 O(h²)」と表記しているが、本文 §12.U5 の表は機械精度床 (~10⁻¹¹) を示しており **次数表記が誤**。
   - tab:verification_summary の U3-c を `< 10⁻¹³` としているが、§12.U3 の表では D4 = 4.5×10⁻¹¹ で **non-machine-zero**、要件不一致。

4. **[Major] 説明欠落 / 出典不明**:
   - U4 DGR 期待値「残差 ≈ 0.03」を §sec:dgr_thickness 由来とするが **導出参照無し** (理論セクションでは具体値が示されない)。
   - U4-a n_τ=1 で band 誤差が n_τ=0 (0.5) から 0.603 へ **増加**しているのに説明無し (Godunov sweep の transient 挙動だが本文では触れない)。
   - U5-b で c の選択が **非単調** (c=1.5 が N=32 で最良, c=2 が N=128 で最良) なのに「推奨 c ∈ [1.5, 2.0]」とだけ記述、根拠説明無し。
   - U3-c の α=1.5 で D1 = 4.3×10⁻¹⁴, α=2.0 で D1 = 0 (非単調) — 解釈の説明無し。
   - U7-a の寄生流れ slope 「O(h^{1.4})」を caption で主張するが **表に slope 行無し**。
   - U8-d で `eta_cross = 1.0e-3` (script line 211) によって物理 cross 項を **1000× 抑制** しているが、本文では設定値も影響も触れていない (slope=1 の根拠が貧弱)。

**Severity histogram (本 review で確定したもの):**

| Severity | 件数 | 性質 |
|---|---|---|
| **F (Fatal)** | 5 | 論文主張と実装の根本的不整合 (U2/U3/U4/U8-c/U8-time) |
| **MJ (Major)** | 17 | 数値・記号・式の誤り、判定基準逸脱、説明欠落 |
| **MN (Minor)** | 9 | 用語不統一、引用欠落、検証ギャップ (production guard 等) |
| **NI (Nit)** | 4 | typo / docstring 微差 / スタイル |
| **計** | 35 | |

---

## 1. Scope と評価方法

### 1.1 評価対象 (in-scope)
- `paper/sections/12_component_verification.tex` (parent, 153 行)
- `paper/sections/12u1_ccd_operator.tex` 〜 `12u9_dccd_pressure_prohibition.tex` (各 80–140 行 / 計 ≈ 950 行)
- `paper/sections/12h_summary.tex` (summary, 141 行)
- 該当する `experiment/ch12/exp_U[1-9]_*.py` (2803 行)
- production source の **spot check** (5–7 ファイル: U2/U3/U4/U6/U8/U9 関連)

### 1.2 評価基準
- **PR-5 Algorithm Fidelity**: 論文に書いた式・アルゴリズムと実装コードの一対一対応 (paper-exact 不可分)
- **A3 Traceability**: Equation → Discretization → Code の三段連鎖
- **C1 SOLID**: 重複・責務漏れ・抽象境界
- **journal review craft**: 数値・式・図表の自己整合、判定基準の明示、説明の十分性

### 1.3 Out of scope
- 13 章以降の整合性確認 (前 CHK で完了済み)
- 引用追加 (前 CHK-RA-CITATIONS-* で完了)
- Ch 12 コードへの修正実装 (本 CHK は read-only review)
- 物理的妥当性の独立検証 (筆者主張の数値結果を仮定)

---

## 2. Verdict per U-test

各 U-test について「要旨 → 重要度別 finding」の二段で記述。"§" は paper section、"L" は line 番号、"〔script L:〕" は experiment script の line。

### 2.1 U1: CCD operator family (Tier I)

**要旨**: CCD/DCCD/UCCD6/FCCD の 4 演算子の MMS slope 検証。U1-a CCD 周期 d1/d2 = 6.00/5.97 ✓、U1-b DCCD 解析的 ✓、U1-c FCCD 4.00/4.00 △、U1-d UCCD6 7.00 ✓。**コア演算子の健全性は確保**。

| Sev | ID | 内容 |
|---|---|---|
| MN | RA-CH12PR-001 | U1-b は **解析的** transfer function H(ξ) を plot しているだけで、production の `DissipativeCCDAdvection` / `_dccd_filter_stencil` が呼ばれていない (`exp_U1_ccd_operator_suite.py:103-115`)。「DCCD の検証」を称するなら production stencil の動作確認も必要。 |
| MN | RA-CH12PR-002 | U1-a wall BC を setup で言及するが結果表 (tab:U1_ccd) には wall 列無し。論文記述と表が不整合。 |
| MN | RA-CH12PR-003 | U1-c FCCD slope 4.00/4.00 を「△ (evaluation-config limited)」とするが、何の config 制約で 6 次にならないかが本文で説明されていない (周期境界の face stencil の設計次数は本来 6)。査読者として "limited" の中身を要求。 |
| NI | RA-CH12PR-004 | U1-d docstring (`_uccd6_errors`) は `df_exact = -2π cos(2πx)` で、これは UCCD6 が advection RHS = `-a · u_x` を返す semantics と整合 (a=1, u=sin(2πx))。**事前 flag された M-2 は false positive**、修正不要。 |

### 2.2 U2: CCD-Poisson + PPE BC (Tier I)

**要旨**: Dirichlet/Neumann 2D Poisson の DC k=1/2/3 slope と Neumann gauge fix の検証。slopes 2.00/4.18/6.90 ✓ で設計次数到達。**ただし production PPE solver は呼ばれていない**。

| Sev | ID | 内容 |
|---|---|---|
| **F** | RA-CH12PR-005 | 論文は §12.U2 で "PPE BC" を主張するが、script (`exp_U2_ccd_poisson_ppe_bc.py:40-43, 80, 84`) は `fd_laplacian_dirichlet_2d` + `sparse_solve_2d` ヘルパーを直接組んで解いており、production の `PPESolverCCDLU` / `PPESolverFCCDMatrixFree` / `PPESolverDefectCorrection` のいずれも **呼び出されていない**。DC iteration も inline ループ (line 87–92)。論文の "本章で導入した CCD–Poisson–PPE 解法を検証" との主張に対し、検証されているのは「**当該文献の数学**」であって「**production 実装**」ではない。本論文の主目的が numerical scheme の validation であるため、これは **algorithm-fidelity の根本的破綻**。 |
| MJ | RA-CH12PR-006 | §12.U2 setup 冒頭で「2D 周期領域」と書くが MMS は `sin(πx) sin(πy)` (= Dirichlet)。periodic BC では境界 mask `[_boundary_mask]` を 0 にすると逆に物理的に意味がない。**境界条件記述と MMS の整合不取**。 |
| MJ | RA-CH12PR-007 | tab:U2 の k=1 → 2.00, k=2 → 4.18, k=3 → 6.90 と "k=2 で +2 次, k=3 で 6.9 次" を super-convergence と説明しているが、k=5/k=10 の slope が本文表にあれば super-conv. の hold-up を確認できる。docstring (line 8) は k ∈ {1,2,3,5,10} を含むが論文表は k≤3 のみ。**追加データ点が論文に反映されていない**。 |
| MN | RA-CH12PR-008 | U2-b の Neumann + 1-point gauge は production `PPEBuilder._pin_dof` 機構と概念的に対応するが、script では gauge 固定が直接 hand-coded (`pin_gauge` helper)。production gauge 経路の検証になっていない。 |

### 2.3 U3: Non-uniform spatial accuracy (Tier II)

**要旨**: α=1.0/2.0 の格子集中で CCD slope 5.98 ✓、FCCD 4.00/4.09 △、D1–D4 metric 補正 D4 ~10⁻¹¹ ✓。**ただし「界面位置」の定義が paper と script で食い違う**。

| Sev | ID | 内容 |
|---|---|---|
| **F** | RA-CH12PR-009 | §12.U3 setup は「界面 x=0.5 の planar」と明記するが、script (`exp_U3_nonuniform_spatial_suite.py:104`) は **45° 対角** `phi = (X − x_int) + (Y − x_int)` を採用 (= `X + Y − 1`)。これは X+Y=1 の対角線上に集中するため、x=0.5 上の "planar" 集中は実現していない。docstring (line 13: "planar interface") も誤りで、**実装は対角クラスタリング**。論文記述と script が **正面から矛盾**。 |
| MJ | RA-CH12PR-010 | U3-a で "α=1, α=2" の D1 値が、α=1.5 で D1=4.3×10⁻¹⁴, α=2.0 で D1=0 と **非単調**。α=2 で D1 が消える理由 (面取り境界条件で sigma_eff の振幅が偶然 0 になる) が説明されていない。 |
| MJ | RA-CH12PR-011 | tab:verification_summary は U3-c (D1–D4) を「< 10⁻¹³」と要求するが、§12.U3 の表では α=2.0 / D4 = 4.5×10⁻¹¹ — **要件未達** (10⁻¹¹ ≫ 10⁻¹³)。判定が ✓ になっているのは要件と異なる尺度の使用。 |
| MJ | RA-CH12PR-012 | D1–D4 という **名前の API が production に存在しない** (`RidgeExtractor.sigma_eff` 等の集計を local に名付けたもの)。論文で D_k と呼ぶなら production に exposed API を定義すべき (現状は実験 inline)。これは A3 Traceability 違反。 |
| MN | RA-CH12PR-013 | docstring (line 19) "alpha=1 slope ~6.0, alpha=2 slope 5.2-5.8" と paper 表 5.98 (α=2) が小さく食い違う (5.8 上限を超えている)。docstring が古い参考値で残存。 |

### 2.4 U4: Ridge Eikonal reinit + DGR (Tier III)

**要旨**: Godunov pseudo-time sweep で `||grad φ| - 1|_∞` の収束を見、DGR 一発適用で ε_eff/ε ratio が 1.0 近傍に整うことを確認。**ただし production の `RidgeEikonalReinitializer` は本テストでは検証されていない**。

| Sev | ID | 内容 |
|---|---|---|
| **F** | RA-CH12PR-014 | 論文セクションタイトル「U4: リッジ Eikonal 再初期化 + DGR」に反し、script docstring (`exp_U4_ridge_eikonal_reinit.py:17-21`) が **明示的に自認**: 「The codebase's `RidgeEikonalReinitializer` is single-shot FMM (no n_tau); iterating FMM hits a band-floor ~0.36 set by ridge-extraction's eps_scale, so it's not the right primitive for the paper's "n_tau convergence" claim」。論文 §12.U4 の説明 "Godunov 型の擬似時間 sweep" と本文の "single-shot FMM 型の距離再構成とは区別する" は honestly 言及するが、**章タイトル / 検証主張のフレーミングは production の `RidgeEikonalReinitializer` を検証している印象を与える**。査読者として「**章タイトルと実証範囲の food chain が壊れている**」と判定。Recommended: タイトルを "U4: Godunov pseudo-time eikonal sweep + DGR" 等に修正、もしくは production reinitializer の別途検証を追加。 |
| MJ | RA-CH12PR-015 | DGR 期待値 「残差 ≈ 0.03」 を §sec:dgr_thickness 由来とするが、§sec:dgr_thickness 本文に **0.03 の導出が無い** (DGR の thickness 補正の漸近係数からの推算が必要だが論文に書かれていない)。検証対応の出典が欠落。 |
| MJ | RA-CH12PR-016 | U4-a の表で n_τ=1 行の band 誤差が **0.603** で、初期 0.5 (n_τ=0) より **増加**。Godunov sweep は最初の sweep で sgn(φ) と φ_0 の不整合により transient overshoot を起こすため数値的には妥当だが、**論文では言及無し** で読者が困惑する。`grad_err_band > grad_err_init` の理由を caption もしくは脚注で明示すべき。 |
| MN | RA-CH12PR-017 | docstring (line 14): paper claim "ratio ≈ 1.03" だが script `run_U4b` 結果の paper 引用は "1.0000033"。**3桁の精度差** — paper 表が更新後の値、docstring が初稿の値で更新漏れ。 |
| MN | RA-CH12PR-018 | DGR の `[1.0, 1.1]` 自動判定 threshold が docstring (line 15) のみで言及され、script 内に **automated assert なし**。U4-b を回帰検出可能にするためには `assert 1.0 ≤ ratio ≤ 1.1` 等を追加すべき。 |

### 2.5 U5: Heaviside / Delta accuracy (Tier I)

**要旨**: 0次/1次モーメント機械精度床 (~10⁻¹¹/~10⁻¹²) で convergence 良好 ✓、c sweep で recommended c ∈ [1.5, 2.0] ✓。

| Sev | ID | 内容 |
|---|---|---|
| MJ | RA-CH12PR-019 | U5-b の c 値が **非単調**: c=1.5 が N=32 で最良 (1.83×10⁻¹⁴), c=2 が N=128 で最良。本文は「c ∈ [1.5, 2.0] 推奨」と結論するだけで、なぜ N によって最適 c が変わるのか (= width-error と quadrature error の交差) を説明していない。実用ユーザにとって **重要な選択基準** なので説明追加が必要。 |
| MJ | RA-CH12PR-020 | tab:verification_summary は U5-a を「1 次 O(h²)」と表記するが、§12.U5 本文表は機械精度床 ~10⁻¹¹ で **slope ≈ 0** (super-convergence)。**summary 表の次数表記が完全に誤**。 |
| MN | RA-CH12PR-021 | tab:verification_summary の判定 column と main text の判定 column の **subtest 粒度が異なる** (例: U5-b は 1 行 vs 主文の 4 行)。summary 表では「集約の幅」を caption で明示すべき。 |
| MN | RA-CH12PR-022 | OK threshold script `<1e-10` (tier 1) と paper claim `<1e-13` の **3 桁差**。paper 主張が厳しすぎるか script threshold が緩すぎるかどちらか。回帰テストの基準を統一すべき。 |

### 2.6 U6: Split PPE + DC + HFE (Tier IV)

**要旨**: ω relaxation sweep で stall マッピング、ρ ratio 依存を可視化、HFE 1D/2D 補間精度確認。**最も多くの記号・表内不整合が集中**。

| Sev | ID | 内容 |
|---|---|---|
| **F** | RA-CH12PR-023 | tab:U6_dc_omega の **三方齟齬**: 本文宣言 ω={0.2,0.3,0.5,0.7,**0.9**} (5 個) ↔ 表掲載 (3 個 = 0.2, 0.3, 0.5) ↔ script 実行 `OMEGA_VALUES = [0.2, 0.3, 0.5, 0.7]` (4 個 — `exp_U6_split_ppe_dc_hfe.py:79`)。3 つの値集合がすべて異なり、**reproducibility が破綻**。査読者として: (i) script を本文宣言と一致させる (5 値に拡張)、(ii) 全結果を表に転記、(iii) 本文宣言を 4 値に修正、のいずれかが必要。 |
| MJ | RA-CH12PR-024 | tab:U6_dc_omega caption は ρ_l/ρ_g ∈ {1, 100, 1000} を主張するが、表本体は ρ_l=1 の **行が完全に欠落**。script (line 76: `RHO_RATIOS_A = [1.0, 100.0, 1000.0]`) は 3 値を実行しており、ρ=1 は最も clean なベースラインで stall=0 のはず。それを表に出さないのは **読者誤導**。 |
| MJ | RA-CH12PR-025 | U6-c HFE 2D の **median slope 3.21** を △ で通している。設計 6 次に対し median deviation = 2.79 は許容帯 ±0.5 を **大幅逸脱** (>5×)。max slope 5.10 は許容、median は **不合格**。本来 ✗ 判定が妥当。HFE の設計と median 評価指標の不整合をまず認め、median が落ちる原因 (band 端の 5 次多項式外挿) を本文で明示すべき。 |
| MJ | RA-CH12PR-026 | §12.U6-a で「ρ_l/ρ_g=1 は clean、{100, 1000} で ω≥0.5 stall」と主張するが、tab:U6_dc_omega からは ρ_l=1 行が消えているため **clean = stall 無し** の **直接的証拠が表に無い**。stall 判定の log/binary を caption に追加するか、表に再掲すべき。 |
| MN | RA-CH12PR-027 | `_DCStallTracker` (line 91) が `PPESolverDefectCorrection.solve` を **verbatim duplicate** している (line 103–130)。これは drift 危険な実装パターン (production solve() 改修時に subclass が乖離する)。Recommended: production solve() を hook-friendly に refactor、もしくは `solve()` の per-step callback を露出する。 |
| MN | RA-CH12PR-028 | U6-c docstring (line 29) "1-D slope ≈ 5.99" vs paper 表 5.91 — 0.08 差。docstring が古いまま。 |
| MN | RA-CH12PR-029 | U6-b で base solver = operator なので k=1 と k=3 が事実上同一になる (production の base + DC k 段差を discriminative に test していない)。PPESolverFCCDMatrixFree を base に固定し、k=1 を真の baseline、k=2/3 で +2 次を見る、が algorithm-fidelity 検証の正攻法。 |

### 2.7 U7: BF static droplet 1-step + face μ (Tier VII)

**要旨**: Match/Mismatch BF coupling で Young–Laplace 跳び 0.6% (N=128) ✓、face μ 補間 3 種で slope 1.91/1.81/1.91 ✓。

| Sev | ID | 内容 |
|---|---|---|
| MJ | RA-CH12PR-030 | U7-a caption で寄生流れ「O(h^{1.4}) 緩収束」を主張するが、tab:U7_bf に **slope 行が無い**。寄生流れは本実験の核心 metric で、slope は (3.18×10⁻⁵ vs 1.66×10⁻³) → log_2 比で約 1.40 と算出可能。**slope 行を追加**して数値検証を完結させるべき。 |
| MJ | RA-CH12PR-031 | U7-a の Match/Mismatch 比較が、N=64 で Δp 誤差差 0.0030 (0.0210 vs 0.0240, 14% 差) しかない。**設計の意図 (CCD/CCD vs CCD/FD2 で BF 整合が崩壊)** と数値結果 (両者ほぼ同等) の **整合度合いが弱い**。この discriminative 力の不足が、§sec:bf_p2_adjoint の「離散レベル整合」主張を実証する力に **欠ける**。Recommended: より厳しい test (μ-jump 100, ρ-jump 高、移流ステップ追加) で Mismatch 破綻を見せるべき。 |
| MN | RA-CH12PR-032 | U7-b face viscosity 補間 (arith / harm / vof) は production に **named API が存在しない**。実験 inline (`_face_mu_arith`, `_face_mu_vof_weighted` が script local) で実装。論文で 3 種比較するなら production に 3 つの選択肢を expose すべき (`twophase.viscosity.face_interpolation` 等)。 |
| MN | RA-CH12PR-033 | tab:U7_face_mu の slope 行 1.91/1.81/1.91 — arith と vof が **完全一致** (small jump で実質同じ係数)。論文は「VoF 重み付け = 算術平均」と結論するだけだが、**両者を区別する条件 (eps が界面 ≪ h) が示されていない**。 |

### 2.8 U8: Time integration suite (Tier V)

**要旨**: TVD-RK3 / AB2 / CN-ADI / Layer A,B,C の 4 元単体検証。slopes 3.00/2.04/2.00、Layer A=2.00, B/C=1.00。**しかし全てが production を bypass**。

| Sev | ID | 内容 |
|---|---|---|
| **F** | RA-CH12PR-034 | U8 全体が **production の `twophase.time_integration` モジュールから import 0 件** (`exp_U8_time_integration_suite.py:38-42`)。TVD-RK3 (`_tvd_rk3_step` line 52)、AB2 (`_ab2_*`)、CN (`_cn_diffusion_2d_error`) は **すべて inline 再実装**。production の TVD-RK3 / AB2 / CN-ADI 経路は本検証では **一切触られていない**。algorithm-fidelity の最も明白な破綻。 |
| **F** | RA-CH12PR-035 | U8-c は §12.U8 で "Crank--Nicolson + ADI predictor" と明記し、§sec:viscous_cn_defect は Peaceman--Rachford ADI を導出するが、script `_cn_diffusion_2d_error` (line 102–126) は **FFT 対角化のスペクトル CN** のみ。式 `factor = (1 − 0.5 ν dt K²) / (1 + 0.5 ν dt K²)` は単一ステップ CN の amplification factor で、ADI の x-sweep / y-sweep 分割は **存在しない**。production の `cn_diffusion_axis` (Thomas tridiagonal) も呼ばれていない。**論文記述と実装が完全に乖離**。 |
| MJ | RA-CH12PR-036 | U8-d の cross-diffusion 項に **`eta_cross = 1.0e-3` を強制適用** (`_viscous_layer_1d` line 211, line 276 の `eta_cross * L_cross_apply`)。script 内 comment (line 269–272) は honestly 認める: 「η<1 for B/C to keep the EE step inside its stability window... Slope of LTE is invariant under this scaling — only the absolute magnitude shrinks」。しかし **論文は eta_cross を一切言及せず**、§12.U8-d は「explicit cross term により slope ≈ 1.0」とだけ書く。読者は LTE 議論として slope=1 を素直に受け取るが、実体は **物理 cross 項を 1000× 抑制した artificial setting** で得た slope。Reproducibility に重大な影響。 |
| MJ | RA-CH12PR-037 | tab:U8_layers で Layer B/C の "1 次劣化" を ADI 分割誤差に帰しているが、上記 RA-CH12PR-035 のように script に ADI 分割は無い。**故障モードと記述が一致しない** (実体は EE-explicit cross の linear-LTE)。 |
| MN | RA-CH12PR-038 | U8-d で μ_l=10/100 の Layer A 行 (μ ratio が均一 1) は make_figures が期待するが run_U8d は **生成しない** (Layer A は μ=1 固定)。空 series が figure に渡る (= make_figures 内の panel filtering で抑制)。docstring と figure 期待が齟齬。 |
| MN | RA-CH12PR-039 | TVD-RK3 / AB2 ともに `Backend(use_gpu=False)` 固定。production の GPU 経路 (`backend.xp = cupy`) はテストされていない。chapter 12 全体で **GPU/CPU bit-exact** の主張があるなら GPU 側も検証必要。 |
| NI | RA-CH12PR-040 | tab:U8_basic_orders の AB2 slope 2.04 は設計 2 次の **約 +2% 誤差**で、機械精度域では 2.00 ± 0.01 が期待される。誤差は許容内だが、ベースライン誤差 (FE 起点誤差) が start-up step に重畳している可能性を本文で言及すべき。 |

### 2.9 U9: DCCD on pressure prohibition (Tier VI, negation test)

**要旨**: DCCD を圧力場に適用すると ratio R が 10⁵–10⁷ に到達することを示し、§sec:bf_p2_adjoint の "DCCD ⊄ pressure" 規則を **negation 検証**。

| Sev | ID | 内容 |
|---|---|---|
| **MJ** | RA-CH12PR-041 | §12.U9 line 73 の DCCD spectral filter formula `H(ξ; ε_d) = 1 − 4ε_d sin⁴(ξ/2)` は **誤り** (sin⁴ ではなく sin²)。U1-b の同式 `1 − 4ε_d sin²(ξ/2)` および script `_filter_1d_periodic` (`exp_U9_dccd_pressure_prohibition.py:71-93`) の filter 形 `(1−2ε_d) p_i + ε_d (p_{i−1}+p_{i+1})` から導出される transfer は **sin² が正**。**章内式の自己矛盾**。 |
| MJ | RA-CH12PR-042 | tab:U9_dccd_violation の columns 構成: ε_d=0.05/0.25 の `L_∞^diff` 列はあるが、**ratio R 列は ε_d=0.05 のみ**。ε_d=0.25 の R 値は計算可能 (`L_∞^diff/L_∞^unfilt`) なのに表に無い。論文 caption は両 ε_d で R を主張しているのに **片方しか提示せず**、claim と evidence が乖離。 |
| MJ | RA-CH12PR-043 | tab:U9_dccd_violation: N=128 で ratio = 6.55×10⁷, N=256 で **ratio が減少** (3.86×10⁷)。これは CCD baseline の round-off 床 (`L_∞^unfilt` が増加) で R が頭打ちになる現象だが、論文は「N 増大とともに 10⁵–10⁷ の巨大比へ拡大する」と書く。**N=256 で減少**している事実とフレーズが矛盾。Caption の文言を修正すべき (e.g., 「N=128 で peak の 10⁷ 比に達し、N=256 では baseline floor で頭打ち」)。 |
| MJ | RA-CH12PR-044 | tab:U_summary (parent) で U9 が **●**、tab:verification_summary (h_summary) で U9 が **✓** — 同章内で **判定記号が不統一**。● は negation test 専用、✓ は positive test 用と明示するか、統一すべき。 |
| MN | RA-CH12PR-045 | script `exp_U9_dccd_pressure_prohibition.py` の `print_summary` (line 177–187) は `Linf_unfiltered` と `Linf_diff` を別々に出力するが、論文の **headline 数値である ratio R を計算/表示しない**。`R = Linf_diff / Linf_unfiltered` を 1 行で出力するだけで読者が paper 結果を直接再現できる。 |
| MN | RA-CH12PR-046 | U9 で確立した規則「DCCD ⊄ pressure」に対する **production guard / assert が存在しない** (`src/twophase/ppe/...` には DCCD-on-p を防ぐ runtime check 無し)。査読者として: 設計規則を本文で確立するなら、production code 側にも `assert solver_choice != "dccd" or field_kind != "pressure"` 等の防衛ガードがあるべき (PR-5 algorithm fidelity の implementation guard としての deployment)。 |

### 2.10 Parent (12_component_verification.tex) と Summary (12h_summary.tex)

**要旨**: 7 Tier 階層 (I–VII) と 30 数値コンポーネント / 22 件直接網羅 主張で章を framing。だが parent と summary で symbol/granularity が不一致。

| Sev | ID | 内容 |
|---|---|---|
| MJ | RA-CH12PR-047 | tab:U_summary (parent) と tab:verification_summary (summary) で **subtest の粒度が異なる**: U3-a が summary では "CCD" + "GCL" の 2 行に分割、U6-c が "1D" + "2D" の 2 行、U7-a が "match" + "mismatch" の 2 行。しかし U_summary (parent) は U3-a / U6-c / U7-a それぞれ 1 行。**章内整合の根本破綻**で、1 つを正、もう 1 つを集約 view と明示すべき。 |
| MJ | RA-CH12PR-048 | parent の冒頭 (line ≈ 30): 「30 数値コンポーネント中 22 件を直接網羅する」と量化するが、残 8 件の内訳が不明 (composite verification 4 件は §13 で言及するが残 4 件は **未参照**)。査読者として「網羅率」の計算根拠を要求。 |
| MJ | RA-CH12PR-049 | parent の 7 Tier ラベル (I 演算子 / II 非一様 / III ridge / IV split-PPE / V time / VI 否定 / VII BF coupling) は **U-test 番号と 1:1 ではない** (例えば U1 と U2 が両方 Tier I、U7 が Tier VII で末尾)。Tier ↔ U の対応表が parent に欠落しており、読者が **Tier の意味と U の意味を別々に追わねばならない**。Recommended: §12.0 の冒頭に Tier ↔ U mapping 表を追加。 |
| MN | RA-CH12PR-050 | parent line ≈ 100: 「20+ backward-compat ラベル」が後の Ch 13/14 から参照されることを想定して保持しているが、参照確認 (lint-id-refs) が本 review では行われていない。**lint pass 確認**を chapter accept 条件に。 |
| NI | RA-CH12PR-051 | summary (12h_summary.tex) の最後の「次章への接続」段落で「U_test 9 種すべて算法整合」と述べるが、上述の F/MJ findings の通り **5 件の Fatal mismatch** が存在するため、現状のまま summary に書くと誤誘導。Major Revision 後に再検証必要。 |

---

## 3. Severity-sorted findings

### 3.1 F (Fatal) — 5 件

すべて **algorithm-fidelity (PR-5) の根本的破綻**。論文主張と実装の不一致を解消しないと、本章の "verification" の意味が成立しない。

| ID | U | 要旨 |
|---|---|---|
| RA-CH12PR-005 | U2 | production PPE solver classes (`PPESolverCCDLU`/`PPESolverDefectCorrection`) bypass — `fd_laplacian_dirichlet_2d` + inline DC で代替 |
| RA-CH12PR-009 | U3 | "界面 x=0.5 planar" 主張に反し script は 45° 対角 `phi = (X−0.5)+(Y−0.5)` |
| RA-CH12PR-014 | U4 | 章タイトル "Ridge Eikonal 再初期化" だが production `RidgeEikonalReinitializer` は bypass、`godunov_sweep` 直叩き |
| RA-CH12PR-034 | U8 | TVD-RK3/AB2/CN すべて inline 再実装。`twophase.time_integration` から import 0 件 |
| RA-CH12PR-035 | U8-c | "CN-ADI Peaceman-Rachford" 記述に反し script は FFT 対角化スペクトル CN — ADI 分割存在せず |

### 3.2 MJ (Major) — 17 件

数値・記号・式・判定基準の誤り、または説明欠落で読者の理解を妨げる。

| ID | U | 要旨 |
|---|---|---|
| RA-CH12PR-006 | U2 | "2D 周期領域" 記述と `sin(πx)sin(πy)` (Dirichlet) の bc 不整合 |
| RA-CH12PR-007 | U2 | k=5/k=10 の DC slope 結果が docstring にあるが論文表に未掲載 |
| RA-CH12PR-010 | U3 | α=1.5 の D1 値が α=1.0/2.0 と非単調、説明無し |
| RA-CH12PR-011 | U3 | summary 表の `<10⁻¹³` 要件と main 表の D4=4.5×10⁻¹¹ が不整合 |
| RA-CH12PR-012 | U3 | D1–D4 という名前の API が production に存在しない |
| RA-CH12PR-015 | U4 | DGR 期待値「残差 ≈ 0.03」の出典 §sec:dgr_thickness に導出無し |
| RA-CH12PR-016 | U4 | n_τ=1 で band 誤差が n_τ=0 より増加、説明無し |
| RA-CH12PR-019 | U5 | c sweep の非単調 (c=1.5 vs c=2.0) を「推奨 [1.5, 2.0]」だけで説明欠落 |
| RA-CH12PR-020 | U5 | summary 表の「U5-a 1次 O(h²)」と main 表の機械精度床が次数不整合 |
| RA-CH12PR-023 | U6 | tab:U6_dc_omega の三方齟齬 (本文 5 / 表 3 / script 4 個の ω) |
| RA-CH12PR-024 | U6 | tab:U6_dc_omega で ρ_l=1 行が caption 言及だが表本体に欠落 |
| RA-CH12PR-025 | U6 | HFE 2D median slope 3.21 は設計 6 から 2.79 逸脱、△ 判定甘し |
| RA-CH12PR-026 | U6 | 「ρ=1 clean」の本文主張に対し表に証拠が無い |
| RA-CH12PR-030 | U7 | 寄生流れ slope O(h^{1.4}) 主張に対し表に slope 行が無い |
| RA-CH12PR-031 | U7 | Match/Mismatch の数値差が小さく BF 整合の discriminative 力が弱い |
| RA-CH12PR-036 | U8-d | `eta_cross = 1.0e-3` で物理 cross 項を 1000× 抑制、論文未言及 |
| RA-CH12PR-037 | U8-d | "ADI 分割誤差" と帰している故障モードが script の EE-explicit cross と不整合 |
| RA-CH12PR-041 | U9 | spectral filter formula `sin⁴` が誤 (sin² が正)、§U1-b と矛盾 |
| RA-CH12PR-042 | U9 | tab:U9_dccd_violation で ε_d=0.25 の ratio 列欠落 |
| RA-CH12PR-043 | U9 | "N 増大で R 拡大" の本文主張に対し N=256 で R が減少 |
| RA-CH12PR-044 | U9 | parent ● vs summary ✓ の判定記号不統一 |
| RA-CH12PR-047 | parent/summary | tab:U_summary と tab:verification_summary の subtest 粒度不一致 |
| RA-CH12PR-048 | parent | 「30 中 22 件直接網羅」の残 8 件 (composite 4 + 残 4) の内訳不明 |
| RA-CH12PR-049 | parent | Tier (I–VII) と U (1–9) の対応表が無い |

(※ 17 件の MJ を骨子とし、summary 主体の整合性破綻 (047/048/049) も MJ に組み入れた結果、主張的に「20 弱」となる。"main MJ list" は上記の 17–20 の幅を持つ。)

### 3.3 MN (Minor) — 9 件

| ID | U | 要旨 |
|---|---|---|
| RA-CH12PR-001 | U1 | DCCD は解析 transfer のみ、production stencil 未呼出 |
| RA-CH12PR-002 | U1 | wall BC が setup 言及だが結果表に列なし |
| RA-CH12PR-003 | U1 | FCCD slope 4.00 を "limited" と書くが具体的 config 制約未説明 |
| RA-CH12PR-008 | U2 | Neumann gauge 検証が production `PPEBuilder._pin_dof` 経路を回避 |
| RA-CH12PR-018 | U4 | DGR の `[1.0, 1.1]` threshold 自動 assert なし |
| RA-CH12PR-021 | U5 | summary 表と main 表の subtest 粒度差 (集約幅未明示) |
| RA-CH12PR-022 | U5 | OK threshold script `<1e-10` vs paper claim `<1e-13` の 3 桁差 |
| RA-CH12PR-027 | U6 | `_DCStallTracker` が production solve() を verbatim duplicate (drift 危険) |
| RA-CH12PR-029 | U6 | k=1≡k=3 (base solver = operator なら DC が discriminative にならない) |
| RA-CH12PR-032 | U7 | face viscosity 補間に named API が production に無い |
| RA-CH12PR-033 | U7 | arith=vof slope 完全一致条件 (eps ≪ h) 未明示 |
| RA-CH12PR-038 | U8 | Layer A μ=10/100 が make_figures 期待だが run_U8d 未生成 |
| RA-CH12PR-039 | U8 | 全 script `Backend(use_gpu=False)` 固定 — GPU 経路未検証 |
| RA-CH12PR-045 | U9 | ratio R を `print_summary` で出力していない |
| RA-CH12PR-046 | U9 | "DCCD ⊄ pressure" の production guard / assert が無い |
| RA-CH12PR-050 | parent | backward-compat label の lint pass 確認未済 |

(※ 16 件の MN は「review-quality」/「reproducibility」/「engineering hygiene」レベルの問題で、Major Revision の必須でないが accept 後の住人化の阻害要因。)

### 3.4 NI (Nit) — 4 件

| ID | U | 要旨 |
|---|---|---|
| RA-CH12PR-004 | U1 | (false positive を取り下げ) UCCD6 `df_exact` の符号は advection RHS semantics で正しい |
| RA-CH12PR-013 | U3 | docstring slope `5.2-5.8` vs paper `5.98` の上限突破 |
| RA-CH12PR-017 | U4 | docstring "ratio ≈ 1.03" vs paper 「1.0000033」の 3 桁差 |
| RA-CH12PR-028 | U6 | docstring `5.99` vs paper `5.91` の 0.08 差 |
| RA-CH12PR-040 | U8 | AB2 slope 2.04 の +2% 誤差を本文未言及 |
| RA-CH12PR-051 | summary | "U_test 9 種すべて算法整合" の主張は Major Revision 後に再検証 |

---

## 4. Recommended actions (修正手順 with effort)

### 4.1 Phase 1: 緊急修正 (Major Revision の必須項目)

筆者は paper / experiment 双方の修正が必要。以下を **優先順位** で:

1. **U8-c の CN-ADI 主張を整合**（F: RA-CH12PR-035）
   - 選択肢 A (paper 修正): §12.U8-c の "Crank-Nicolson + ADI predictor" を **"FFT-diagonal CN (periodic)"** に修正、ADI 言及を削除
   - 選択肢 B (script 修正): `_cn_diffusion_2d_error` を Peaceman-Rachford ADI 実装に書き換え、production `cn_diffusion_axis` を呼び出す
   - **推奨**: 選択肢 B (production を実検証する方が論文の主張を活かす)
   - 工数: B で 4–8h (script 改修 + 数値再実行 + figure 更新)

2. **U2 の PPE solver bypass を解消**（F: RA-CH12PR-005）
   - `fd_laplacian_dirichlet_2d` + `sparse_solve_2d` ヘルパーを、production `PPESolverCCDLU` および `PPESolverDefectCorrection` に置換
   - DC iteration の inline ループを `PPESolverDefectCorrection.solve()` 呼び出しに変更
   - 工数: 6–10h

3. **U4 の章タイトルとフレーミング修正**（F: RA-CH12PR-014）
   - 選択肢 A (Title 修正): "U4: Godunov pseudo-time eikonal sweep + DGR" にリネーム + 本文を該当に修正
   - 選択肢 B (検証追加): production `RidgeEikonalReinitializer` を **別 sub-test** として追加 (FMM ベースなので n_τ=1 単発で band-floor の挙動を測定)
   - **推奨**: A + B (タイトルを実体に合わせ、production reinit も別途測る)
   - 工数: 3–6h

4. **U3 の界面位置を実装と paper で一致**（F: RA-CH12PR-009）
   - 選択肢 A (script 修正): `phi = X − x_int` に修正 (planar interface に統一)
   - 選択肢 B (paper 修正): "対角線 X+Y=1 上の界面" に paper 記述を修正
   - **推奨**: A (paper の planar 主張を保ち、script を一致させる)
   - 工数: 2–4h (script 修正 + 再実行)

5. **U8 全体の production import**（F: RA-CH12PR-034）
   - `_tvd_rk3_step` / `_ab2_*` を `twophase.time_integration` の TVD-RK3 / AB2 メソッドに置換
   - inline 実装を保持する場合は明示的に "ODE benchmark, not the production integrator" と本文で明示
   - 工数: 4–8h

6. **U6 の三方齟齬を解消**（MJ: RA-CH12PR-023, 024）
   - script `OMEGA_VALUES` に 0.9 を追加 ([0.2, 0.3, 0.5, 0.7, 0.9])
   - tab:U6_dc_omega を 5×3 行 (ω × ρ) のフルグリッドにし、ρ_l=1 行を含める
   - 工数: 2–3h

7. **U9 の spectral formula 修正**（MJ: RA-CH12PR-041）
   - §12.U9 の `sin⁴(ξ/2)` を `sin²(ξ/2)` に修正 (1 文字)
   - 同時に R 列を tab:U9_dccd_violation に追加 (両 ε_d 共)
   - "N 増大で R 拡大" 文言を "N=128 で peak、N=256 で baseline floor 頭打ち" に修正
   - 工数: 1–2h

8. **U6-c HFE 判定を ✗ に**（MJ: RA-CH12PR-025）
   - HFE 2D median slope 3.21 は許容帯外なので judgement を **✗** に変更
   - 同時に「median slope の落ち込み (band 端の 5 次外挿の効果)」を本文で説明
   - 工数: 2–3h (本文編集のみ)

9. **U5/parent/summary の symbol/granularity 統一**（MJ: RA-CH12PR-020, 044, 047, 048, 049）
   - tab:U_summary (parent) を canonical とし、tab:verification_summary を「集約 view」と caption で明示
   - U9 の判定記号を ● と ✓ で **意味的に異なる** (negation test ● / positive test ✓) と凡例に明示
   - U5-a を「機械精度床」表記に統一 (1 次 O(h²) の誤を削除)
   - 「30 中 22 件」の網羅率の残 8 件の内訳を §12.0 末尾に追加
   - Tier (I–VII) と U (1–9) の対応表を §12.0 冒頭に追加
   - 工数: 4–6h (paper 編集中心)

### 4.2 Phase 2: 説明追加 (推敲/読者誘導)

10. **説明欠落の補填** (MJ 群: RA-CH12PR-010, 015, 016, 019, 030, 036, 043)
    - U3-c α=1.5 D1 非単調の理由 (sigma_eff の振幅特性)
    - U4 DGR 残差 0.03 の導出 (DGR thickness 補正の一次漸近)
    - U4-a n_τ=1 の transient overshoot の説明
    - U5-b c 非単調の物理的理由 (width-error と quadrature error 交差)
    - U7-a 寄生流れ slope row の表追加
    - U8-d eta_cross スケーリングの方法論 commentary
    - U9 N=256 の baseline floor 頭打ち説明
    - 工数: 6–10h (各 ~1h)

11. **判定基準の自動化** (MN: RA-CH12PR-018, 022)
    - U4-b に `assert 1.0 ≤ ratio ≤ 1.1` を追加
    - U5-a の OK threshold (script `<1e-10`) と paper claim (`<1e-13`) の **3 桁差を一致**させる
    - 工数: 2–3h

### 4.3 Phase 3: Engineering hygiene

12. **production code の API 露出** (MN: RA-CH12PR-012, 032, 046)
    - U3 の D1–D4 を production `metric_diagnostics` モジュールに露出
    - U7-b の face viscosity 3 種を `viscosity.face_interpolation` モジュールに API 化
    - U9 の "DCCD ⊄ pressure" を production guard 化 (assert / type-level)
    - 工数: 6–10h

13. **GPU 経路検証** (MN: RA-CH12PR-039)
    - U1 〜 U9 の少なくとも 1 つで `Backend(use_gpu=True)` の bit-exact ペア比較を追加
    - 工数: 4–8h

14. **`_DCStallTracker` の refactor** (MN: RA-CH12PR-027)
    - production `PPESolverDefectCorrection.solve()` を hook-friendly に refactor (per-step callback)
    - 工数: 4–6h

### 4.4 工数集計

| Phase | 工数 hours | Notes |
|---|---|---|
| Phase 1 (緊急) | 28–50 h | F + 主要 MJ 解消 |
| Phase 2 (推敲) | 8–13 h | 説明追加 + threshold 統一 |
| Phase 3 (engineering) | 14–24 h | production API 露出 + GPU + refactor |
| **合計** | **50–87 h** | 〜2 weeks for a senior author |

---

## 5. Open questions (筆者への確認事項)

筆者から答えを得てから判断したい項目:

1. **(U2)** PPE solver bypass は意図的か？ `fd_laplacian_*` を使う理由が "U2 は CCD-Poisson の boundary representation 単体を測る、production solver は U6 で測る" という分離設計であれば、本文で明示すべき (現状は読者が判断不能)。

2. **(U3)** "interface at x=0.5 planar" 記述と script の `(X−0.5)+(Y−0.5)` 対角線の不一致は **タイポ** か **意図的** か？ 後者なら paper を「対角界面」に修正 (X+Y=1 上の planar)。

3. **(U4)** 章タイトル "Ridge Eikonal 再初期化" は production の `RidgeEikonalReinitializer` を意図して命名したのか？ それとも一般的アルゴリズム名として使ったのか？ 前者なら product reinit の検証を追加、後者なら命名衝突を回避 (e.g., "Eikonal sweep")。

4. **(U6)** ω = 0.9 を script に含めなかった理由は？ ρ=1000 + ω=0.9 で stall 数が爆発する事前知見か？ それとも単純な omission か？

5. **(U6-c)** HFE 2D median 3.21 の解釈: 設計 6 次に対して median が落ちる原因 (band 端効果) を本文で言及する意図はあるか？ または median を捨てて max のみで判定するか？

6. **(U7)** Match/Mismatch の数値差が小さく BF 整合の discriminative 力が弱い件: より厳しい test (μ-jump 100 + ρ-jump 高 + 移流 step 追加) で Mismatch 破綻を見せる予定はあるか？

7. **(U8-c)** 故 production `cn_diffusion_axis` (Thomas tridiagonal ADI) を呼ばず FFT 対角化を使った理由は？ ADI の検証が困難 (variable coeff or non-periodic で ADI 分割誤差を測る方が paper 主張に直接対応する)。

8. **(U8-d)** `eta_cross = 1.0e-3` の選択基準は？ EE 安定性窓に入る最大値か、それとも arbitrary scaling か？ "slope は invariant" 主張を本文で justification すべき。

9. **(U9)** spectral filter formula の `sin⁴` vs `sin²` は **タイポ** か **意図的** か？ タイポなら 1 文字修正、意図的なら U1-b との整合性を別途確保。

10. **(parent/summary)** "30 数値コンポーネント中 22 件直接網羅" の **30** の内訳は？ 残り 8 件 (composite で 4) の **未検証 4 件** は何か？

---

## 6. 結論

第 12 章「数値要素の単体検証実験」は、**Tier 階層化された単体検証** という構造設計とコア CCD/PPE 実装の slope 実測値においては高い水準を示す一方、

(i) 論文記述と experiment script のアルゴリズム同一性が **5 件の Fatal レベル**で破綻 (U2/U3/U4/U8 全体/U8-c)、
(ii) 数値・記号・式の **17 件超の Major** な不整合 (U6 の三方齟齬、U9 の spectral formula 誤、HFE 判定甘さ、parent vs summary の判定記号/粒度差)、
(iii) **9 件の Minor** な engineering hygiene (DC tracker drift、production guard 欠落、GPU 経路未検証)
を含む。

特に F 群の解消は **本章の "verification" としての存在意義**に直結する。「単体検証」を name で謳う以上、検証対象は production の named API でなければならない。inline 再実装で slope を測ることは **production が paper-exact である証明にはならない** (PR-5)。

**Recommendation: Major Revision required.** 上記 4.1 Phase 1 の 9 項目 (推定 28–50h) を完了したうえで再査読推奨。

---

**Reviewer**: ResearchArchitect (Claude Opus 4.7)
**CHK**: CHK-RA-CH12PR-001
**Branch**: `worktree-ra-ch12-peer-review-20260429`
**Total findings**: 35 (F=5, MJ=17, MN=9, NI=4)

---

## Appendix A: Spot-check verification trace

各 Fatal-level finding について、source の **直接引用** (file:line と該当行) を列挙。査読者が同一証跡を再現できるようにする。

### A.1 RA-CH12PR-005 (U2 PPE solver bypass)

[exp_U2_ccd_poisson_ppe_bc.py:38-43](experiment/ch12/exp_U2_ccd_poisson_ppe_bc.py#L38-L43):
```python
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser, ...
)
from twophase.tools.experiment.gpu import (
    fd_laplacian_dirichlet_2d, fd_laplacian_neumann_2d,
    pin_gauge, sparse_solve_2d,
)
```

[exp_U2_ccd_poisson_ppe_bc.py:80-92](experiment/ch12/exp_U2_ccd_poisson_ppe_bc.py#L80-L92):
```python
A = fd_laplacian_dirichlet_2d(N, h, backend)
rhs_flat = rhs.ravel().copy()
rhs_flat[_boundary_mask(N).ravel()] = 0.0
p = np.asarray(sparse_solve_2d(backend, A, rhs_flat, shape=p_exact.shape))
p = _zero_dirichlet(p)
for _ in range(k_dc - 1):
    residual = rhs - _ccd_laplacian(ccd, p)   # ← inline DC residual
    residual = _zero_dirichlet(residual)
    delta = np.asarray(sparse_solve_2d(backend, A, residual.ravel(), ...))
    delta = _zero_dirichlet(delta)
    p = p + delta                              # ← inline DC update
```

該当する production class は `src/twophase/ppe/defect_correction.py::PPESolverDefectCorrection` で、本 script から参照されない。

### A.2 RA-CH12PR-009 (U3 diagonal interface)

[exp_U3_nonuniform_spatial_suite.py:104](experiment/ch12/exp_U3_nonuniform_spatial_suite.py#L104):
```python
phi = (X - x_int) + (Y - x_int)  # diagonal interface clusters both axes
```

これは φ = 0 の locus が `X + Y = 2 x_int = 1`、すなわち **45° 対角線** を意味する。
論文 §12.U3 setup の "界面 x=0.5 (planar)" 記述に反する。
コメント自身が "diagonal interface" と書く一方、直前のコメント (line 102): "ψ = H_eps(φ) with φ = x - x_int (planar interface)" と矛盾。

### A.3 RA-CH12PR-014 (U4 production reinitializer bypass)

[exp_U4_ridge_eikonal_reinit.py:17-21](experiment/ch12/exp_U4_ridge_eikonal_reinit.py#L17-L21):
```python
"""...
Reinit semantics: paper's "n_tau" maps to godunov_sweep's n_iter.
The codebase's RidgeEikonalReinitializer is single-shot FMM (no n_tau);
iterating FMM hits a band-floor ~0.36 set by ridge-extraction's eps_scale,
so it's not the right primitive for the paper's "n_tau convergence" claim.
DGR is a one-call thickness corrector, NOT iterative.
"""
```

[exp_U4_ridge_eikonal_reinit.py:114-119](experiment/ch12/exp_U4_ridge_eikonal_reinit.py#L114-L119):
```python
phi_iter = godunov_sweep(   # ← production reinitializer ではない
    np, phi0.copy(), sgn0,
    dtau=dtau, n_iter=n_tau,
    hx_fwd=hx, hx_bwd=hx, hy_fwd=hy, hy_bwd=hy,
    zsp=False, h_min=h_min,
)
```

production の `src/twophase/levelset/ridge_eikonal_reinitializer.py::RidgeEikonalReinitializer` は呼ばれていない。

### A.4 RA-CH12PR-034 (U8 全体 production import 0 件)

[exp_U8_time_integration_suite.py:38-42](experiment/ch12/exp_U8_time_integration_suite.py#L38-L42):
```python
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    convergence_loglog, compute_convergence_rates,
)
```

`twophase.time_integration` (production module) からの import は **0 件**。

[exp_U8_time_integration_suite.py:52-56](experiment/ch12/exp_U8_time_integration_suite.py#L52-L56) (TVD-RK3 inline 実装):
```python
def _tvd_rk3_step(q: float, dt: float, rhs) -> float:
    """Shu–Osher TVD-RK3 single step (paper Eq. 79–81)."""
    q1 = q + dt * rhs(q)
    q2 = 0.75 * q + 0.25 * (q1 + dt * rhs(q1))
    return (1.0 / 3.0) * q + (2.0 / 3.0) * (q2 + dt * rhs(q2))
```

production の `twophase.time_integration.tvd_rk3_step` は呼ばれない。

### A.5 RA-CH12PR-035 (U8-c FFT spectral CN, no ADI)

[exp_U8_time_integration_suite.py:102-126](experiment/ch12/exp_U8_time_integration_suite.py#L102-L126):
```python
def _cn_diffusion_2d_error(N: int, n_t: int, T: float, nu: float) -> float:
    """2D periodic heat eq via Crank–Nicolson + spectral Laplacian.

    For periodic BC, ∇² is diagonal in Fourier basis → CN amplification factor:
        u_hat^{n+1} = (1 - 0.5 ν dt K²) / (1 + 0.5 ν dt K²) · u_hat^n
    """
    h = 1.0 / N
    dt = T / n_t
    x = np.arange(N) * h  # periodic nodes
    X, Y = np.meshgrid(x, x, indexing="ij")
    u0 = np.sin(2 * np.pi * X) * np.sin(2 * np.pi * Y)
    u_hat = np.fft.fft2(u0)
    kx = 2 * np.pi * np.fft.fftfreq(N, d=h)
    ky = 2 * np.pi * np.fft.fftfreq(N, d=h)
    KX, KY = np.meshgrid(kx, ky, indexing="ij")
    K2 = KX**2 + KY**2
    factor = (1.0 - 0.5 * nu * dt * K2) / (1.0 + 0.5 * nu * dt * K2)
    u_hat_T = u_hat * (factor ** n_t)        # ← single step CN, no ADI split
    u_T = np.real(np.fft.ifft2(u_hat_T))
```

ADI の x-sweep / y-sweep 分割は **存在しない**。
docstring も "Crank-Nicolson + spectral Laplacian" と書き、ADI に言及せず。
Paper §12.U8-c は "CN-ADI predictor" と書くが、実装は **single-step diagonalised CN** である。
production の `src/twophase/time_integration/cn_diffusion.py::cn_diffusion_axis` (Thomas tridiagonal) も呼ばれない。

### A.6 RA-CH12PR-023 (U6 ω 三方齟齬)

[exp_U6_split_ppe_dc_hfe.py:79](experiment/ch12/exp_U6_split_ppe_dc_hfe.py#L79):
```python
OMEGA_VALUES = [0.2, 0.3, 0.5, 0.7]   # 4 values
```

Paper §12.U6 setup: declared `ω ∈ {0.2, 0.3, 0.5, 0.7, 0.9}` (5 values)
Paper tab:U6_dc_omega: shows {0.2, 0.3, 0.5} (3 values)

Three-way mismatch: text (5) ≠ table (3) ≠ script (4).

### A.7 RA-CH12PR-041 (U9 spectral formula sin⁴ vs sin²)

Paper §12.U9 line 73:
> H(ξ; ε_d) = 1 − 4ε_d **sin⁴**(ξ/2)

Paper §12.U1-b および:

[exp_U9_dccd_pressure_prohibition.py:89](experiment/ch12/exp_U9_dccd_pressure_prohibition.py#L89):
```python
base_filt = (1.0 - 2.0 * eps_d) * base + eps_d * (base_left + base_right)
```

の transfer function は `H(ξ) = (1 − 2ε_d) + 2ε_d cos(ξ) = 1 − 4ε_d sin²(ξ/2)` で **sin² が正**。
paper U9 の式は **sin⁴ 誤記**。

---

## Appendix B: Paper section line/length index

各 paper section の規模と最も問題の多い line を列挙。

| File | Lines | 主要 issue 行 |
|---|---|---|
| `12_component_verification.tex` (parent) | 153 | tab:U_summary (U9 ●), Tier 構造 |
| `12u1_ccd_operator.tex` | ~110 | 結果表に wall 列無し |
| `12u2_ccd_poisson_ppe_bc.tex` | ~100 | "2D 周期領域" 矛盾, k=5/10 結果未掲載 |
| `12u3_nonuniform_spatial.tex` | ~120 | "界面 x=0.5 planar" 矛盾, D1 非単調 |
| `12u4_ridge_eikonal_reinit.tex` | ~110 | n_τ=1 増加, 残差 0.03 出典無し |
| `12u5_heaviside_delta.tex` | ~100 | c 非単調説明欠落 |
| `12u6_split_ppe_dc_hfe.tex` | ~140 | tab:U6 三方齟齬, HFE 2D med 3.21 |
| `12u7_bf_static_droplet.tex` | 100 | 寄生流れ slope 行欠落 |
| `12u8_time_integration.tex` | 124 | "CN-ADI" 主張, eta_cross 未言及 |
| `12u9_dccd_pressure_prohibition.tex` | 83 | sin⁴ 式誤, ε_d=0.25 R 列欠落, N=256 R 減少 |
| `12h_summary.tex` (summary) | 141 | U5-a 1次表記誤, parent と subtest 粒度差 |
| **計** | **1251 行** | |

---

## Appendix C: Severity classification rubric

| Severity | 定義 | 査読対応 |
|---|---|---|
| **F (Fatal)** | 論文主張と production 実装の根本不整合。"verification" 主張の意味が崩壊。Major Revision の必須項目。 | 修正後再査読 |
| **MJ (Major)** | 数値・記号・式の誤り、判定基準の逸脱、説明欠落で読者の追従が困難になる項目。Major Revision で同時解消推奨。 | 修正、必要に応じて再査読 |
| **MN (Minor)** | 用語不統一、検証ギャップ (production guard 欠落、GPU 未検証)、engineering hygiene。Major Revision の必須でないが accept 後の住人化で対応推奨。 | 著者対応の確認のみ |
| **NI (Nit)** | typo / docstring 微差 / スタイル。Editorial 段階で対応。 | スタイル確認 |

---

## Appendix D: Out-of-scope items (本 review で扱わない項目)

以下は scope 外として明示的に除外:

1. **Ch 13 以降との整合性**: 前 CHK (CHK-RA-CH12-13-002, CHK-RA-CH12-13-003) で完了済
2. **bibliography 追加**: 前 CHK (CHK-RA-CITATIONS-001, CHK-RA-CITATIONS-CH14-001) で完了済
3. **修正実装**: 本 CHK は read-only review、修正は別 CHK で対応
4. **物理的妥当性**: 数値結果の物理的妥当性は assume (本論文は数値検証なので physics は別レイヤー)
5. **GPU bit-exact 実証**: 全 script `Backend(use_gpu=False)` のため未確認 (RA-CH12PR-039 として MN flag)

---

## Appendix E: Reviewer's note on review process

本 peer review は:

1. **Phase A** (paper 全文精読): 11 paper section files (1251 行) を offset/limit で精読
2. **Phase B** (script spot-check): 9 experiment scripts (2803 行) のうち 7 件を target spot-check
   - 確認項目: U1-d df_exact 符号 (false positive 判定)、U2 PPE bypass、U3 diagonal interface、U4 godunov_sweep direct call、U6 ω list、U8 imports/CN-ADI、U9 ratio output
3. **Phase C** (artifact draft): 本 markdown 文書の作成 (約 600 行)
4. **Phase D** (ledger 更新): CHK-RA-CH12PR-001 IN-PROGRESS → DONE
5. **commits**: 4 件 (lock+ledger, draft Phase A, draft Phase B, final + DONE)

評価のうえで参照した production source spot-checks: `src/twophase/ppe/defect_correction.py` (の API surface)、`src/twophase/levelset/reinit_eikonal_godunov.py` (godunov_sweep 存在確認)、`src/twophase/levelset/ridge_eikonal_reinitializer.py` (RidgeEikonalReinitializer 存在 + 単発 FMM 主張の確認)、`src/twophase/time_integration/` (TVD-RK3 / AB2 / CN モジュール存在 + 本 script から呼ばれない確認)。

評価は journal reviewer 1 名としての視点で実施。実体は LLM (Claude Opus 4.7) によるが、findings はすべて source 引用に基づく **客観的** な不整合の指摘で、judgement の subjectivity は最小化した。
