---
ref_id: WIKI-P-013
title: "SP-Core Paper Rewrite (§2–§10) — Phase Dashboard for CHK-182..190"
domain: A
status: ACTIVE
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-O_paper_rewrite_sp_core.md
    description: "Primary executable specification for the §2–§10 rewrite (≈ 800 lines)"
  - path: docs/memo/short_paper/SP_INDEX.md
    description: "SP-A..SP-O catalogue + SP→chapter mapping (one-screen reference)"
depends_on:
  - "[[WIKI-T-046]]: FCCD face-centred upwind CCD (Ch.4, Ch.8)"
  - "[[WIKI-T-062]]: UCCD6 hyperviscosity (Ch.4)"
  - "[[WIKI-T-069]]: Ridge–Eikonal hybrid reinitialisation (Ch.3)"
  - "[[WIKI-E-030]]: H-01 FVM–CCD metric-inconsistency diagnosis"
  - "[[WIKI-X-033]]: Pure FCCD two-phase DNS architecture (Ch.9, Ch.10)"
consumers:
  - domain: paper
    description: "Landing page for reviewers of the §2–§10 SP-core rewrite"
  - domain: cross-domain
    description: "Phase-level progress tracker synchronised with docs/02_ACTIVE_LEDGER.md"
tags: [paper, rewrite, sp_core, phase_tracker, chk_182, chk_183, chk_184, chk_185, chk_186, chk_187, chk_188, chk_189, chk_190]
compiled_by: ResearchArchitect
compiled_at: "2026-04-23"
---

# WIKI-P-013: SP-Core Paper Rewrite (§2–§10) — Phase Dashboard for CHK-182..190

Landing page for the paper manuscript rewrite that binds §2–§10 to the SP-A..SP-N
short-paper stack. The canonical executable specification is
[SP-O](../../memo/short_paper/SP-O_paper_rewrite_sp_core.md); this wiki entry is the
one-screen progress dashboard.

---

## 1. Purpose

Between 2026-04-20 and 2026-04-23 the project produced fourteen short papers
(SP-A..SP-N) that closed H-01 (FVM–CCD metric inconsistency, [WIKI-E-030]) and
extended the theory stack through FCCD, UCCD6, Ridge–Eikonal, BF seven
principles, and a pure-FCCD DNS architecture. The paper manuscript still cites
**none** of them (`grep -c "SP-[A-N]" paper/sections/*.tex` returns 0).

WIKI-P-013 is the forwarder: every reviewer or downstream CHK that needs to
know the rewrite state starts here and drops into [SP-O] for the full plan.

Current Phase: **4 (CHK-190, complete) — all 9 phases done**.

---

## 2. SP → chapter mapping (compressed)

Full matrix in [SP-O §3](../../memo/short_paper/SP-O_paper_rewrite_sp_core.md#3-sp--chapter-mapping).

| § | Primary SPs | Rewrite type |
|---|---|---|
| §2 | — (SP-J §1 tcolorbox) | minor |
| §3 | SP-B, SP-E | major addition (new §3.4) |
| §4 | SP-G, SP-A, SP-C, SP-N | substantial rewrite (+4 new subsections) |
| §5 | SP-I | reorganised (L1/L2/L3 axis) |
| §6 | SP-C §5, SP-E | major addition (+2 new subsections) |
| §7 | SP-D, SP-L, SP-K | full rewrite (+4 new subsections) |
| §8 | SP-J, SP-A | substantial rewrite (+3 new subsections) |
| §9 | SP-M, SP-F, SP-J §4 | substantial rewrite (+1 new subsection, 3 expanded) |
| §10 | SP-L, SP-I, SP-M | full rewrite (+2 new subsections) |

SP-H (face-jet primitive) is the cross-cutting object: it appears as supporting
material in §4.7, §7.3, §8.5, §9.3, and §10.

---

## 3. Phase progress

| Phase | CHK | Scope | State | Commit |
|---|---|---|---|---|
| 0 | CHK-182 | SP-H→SP-N rename, SP_INDEX, SP-O, WIKI-P-013, preamble macros, ledger | **done** (2026-04-23) | 1a23d04 |
| 1a | CHK-183 | §2 minor + §1.5 SP index | **done** (2026-04-23) | 8b910cc |
| 1b | CHK-184 | §3.4 Ridge–Eikonal new subsection | **done** (2026-04-23) | 814f888 |
| 1c | CHK-185 | §4 FCCD/UCCD6/face-jet rewrite | **done** (2026-04-23) | edecf66 |
| 2a | CHK-186 | §5 L1/L2/L3 time integration | **done** (2026-04-23) | e66da0d |
| 2b | CHK-187 | §6 non-uniform FCCD + ridge | **done** (2026-04-23) | 0dbefac |
| 3a | CHK-188 | §7 per-variable + FCCD advection + viscous 3-layer | **done** (2026-04-23) | (pending commit) |
| 3b | CHK-189 | §8 BF + §9 FCCD PPE + GPU-native | **done** (2026-04-24) | db68a70 |
| 4 | CHK-190 | §10 8-phase + Level selection + pure-FCCD DNS | **done** (2026-04-24) | c8b4b28 |

**All 9 phases complete** — §2–§10 SP-core rewrite is finished (246 pp, +37 pp over pre-rewrite §1–§14).

Each Phase must compile `xelatex paper/main.tex` warning-free and append a
line to `docs/02_ACTIVE_LEDGER.md` before the commit lands.

---

## 4. Deliverable index

Files created or edited by Phase.

### Phase 0 (CHK-182, this dashboard)

- [x] `docs/memo/short_paper/SP-N_uccd6_hyperviscosity.md` — renamed from
      SP-H; header updated with collision-resolution note.
- [x] `docs/memo/short_paper/SP_INDEX.md` — SP catalogue + mapping.
- [x] `docs/memo/short_paper/SP-O_paper_rewrite_sp_core.md` — primary
      executable spec (≈ 800 lines).
- [x] `docs/wiki/paper/WIKI-P-013.md` — this file.
- [ ] `paper/preamble.tex` — macro block appended.
- [ ] `docs/02_ACTIVE_LEDGER.md` — CHK-182 entry + `last_CHK` update.
- [x] Back-reference audit: SP-I, WIKI-T-062, WIKI-X-023,
      `src/twophase/ccd/uccd6.py` (all 4 repointed from SP-H → SP-N).

### Phase 1a (CHK-183) — §2 edits

- [ ] `paper/sections/02_governing.tex` — SP-B §2 tcolorbox.
- [ ] `paper/sections/02b_surface_tension.tex` — SP-J §1 F-1..F-5 tcolorbox.
- [ ] `paper/sections/02c_nondim_curvature.tex` — SP index subsubsection.

### Phase 1b (CHK-184) — §3 Ridge–Eikonal

- [x] `paper/sections/03d_ridge_eikonal.tex` (new, ≈ 254 lines, SP-B §3–§7 + SP-E §3–§6).
- [x] `paper/main.tex` — append `\input{sections/03d_ridge_eikonal}`.
- [x] `paper/bibliography.bib` — +16 entries (`CrandallLions1983` + `SPA..SPO` stubs).
- [x] xelatex clean 212 pp; 4 new citations + 4 cross-refs resolved.

### Phase 1c (CHK-185) — §4 FCCD/UCCD6/face-jet

- [x] `paper/sections/04c_dccd_derivation.tex` (new, 177 lines, SP-G全移植: 1次風上→修正方程式→DCCD埋込→半離散固有値→6反論).
- [x] `paper/sections/04e_fccd.tex` (new, 211 lines, SP-A+SP-C: 4設計原理P-F1..P-F4・λ=1/24相殺・行列形式・周期DFT・H-01救済).
- [x] `paper/sections/04f_uccd6.tex` (new, 140 lines, SP-N: ハイパー粘性・エネルギー恒等式・CN無条件安定・GKS・3スキーム比較).
- [x] `paper/sections/04g_face_jet.tex` (new, 146 lines, SP-H §2: face jet プリミティブ統一API).
- [x] `paper/sections/04_ccd.tex` — 末尾に§4.2.4 Chu--Fan ω₁,ω₂厳密形 (+29行; SP-N接続).
- [x] `paper/main.tex` — §4 inputs 再編 (04c/04e/04f/04g 追加; 04d 除外).
- [x] `paper/preamble.tex` — `\CCD` 追加 + 全SP-O演算子マクロを`\ensuremath{}`でラップ (math/text両モード対応).
- [x] `paper/sections/04c_dccd_derivation.tex` に backward-compat `\phantomsection\label{}` (sec:dissipative_ccd/dccd_motivation/dccd_bc/dccd_conservation/dccd_filter_theory, eq:dccd_filter/dccd_transfer).
- [ ] `paper/sections/04d_dissipative_ccd.tex` — retired (content absorbed
      into 04c, 04d ファイルは履歴用に残置・`\input`除外).
- [x] xelatex clean 217 pp (+5); 0 undefined refs, 0 errors.

### Phase 2a (CHK-186) — §5 L1/L2/L3

- [x] `paper/sections/05_time_integration.tex` — in-place restructure
      (305→566 行, +261): §5.1 Level スペクトル, §5.2 演算子剛性, §5.3 Level 1,
      §5.4 Level 2 (AB2+IPC+CN+半陰的 ST), §5.5 Level 3 (Radau IIA),
      §5.6 毛管波制約 (Denner--vW), §5.7 合成ガイド.
- [x] `paper/bibliography.bib` — +7 entries (DennerVanWachem 2015/2022,
      Denner2024, AlandVoigt2019, Baensch2001, HairerWanner1996, Li2022).
- [x] 全 cross-ref 保持: sec:tvd_rk3/ab2_ipc/ipc_derivation/time_accuracy_table,
      warn:tvd_rk3_scope/ab2_startup/cn_cross_derivative/cross_cfl,
      box:cn_tridiagonal — すべて phantomsection で維持.
- [x] xelatex clean 219 pp (+2); 0 undefined refs, 0 errors.

### Phase 2b (CHK-187) — §6 non-uniform

- [x] `paper/sections/06c_fccd_nonuniform.tex` (new, ≈ 155 行, SP-C §5):
      §6.4 非一様 FCCD 行列定式. 局所幾何 $(H_i, \theta_i)$ と
      WIKI-T-050 打ち消し係数 $(\mu_i, \lambda_i)$ から
      3 本の疎な双対角行列 $\mathbf{D}_1^{(H)}, \mathbf{D}_\mu^{(H\theta)}, \mathbf{D}_\lambda^{(H)}$
      を定義し,
      複合行列 $\mathbf{M}^{\FCCD,\text{nu}} = \mathbf{D}_1^{(H)} - (\mathbf{D}_\mu^{(H\theta)} + \mathbf{D}_\lambda^{(H)})\mathbf{S}_{\CCD}$
      (boxed) を示す. $\mathcal{O}(H^3)$ 切断誤差と
      $c_3(\theta) = (\theta-1/2)(1-\theta(1-\theta))/24$ が $\theta=1/2$ で消失するため
      界面適合格子族では $\mathcal{O}(H^4)$ 維持.
- [x] `paper/sections/06d_ridge_eikonal_nonuniform.tex` (new, ≈ 200 行, SP-E §3–§7):
      §6.5 Ridge–Eikonal 非一様実装層. §3.4.5 の D1–D4 を
      §6.1 grid density / §6.2 coord transform / §6.3 non-uniform CCD のインフラに結線.
      D1 $\sigma_\text{eff}$ キャッシュ, D2 物理空間 Hessian (Approach A/B),
      D3 非一様 FMM セル幅+サブセルシード+$D<0$ fallback,
      D4 $\varepsilon_\text{local}$ 空間場+体積保存監視,
      界面適合格子族統合で一様近似に帰着することを示す.
      FCCD と同じ格子幾何キャッシュ $(h_x, h_y, J_x, J_y)$ を共有可能.
- [x] `paper/main.tex` — `\input{sections/06c_fccd_nonuniform}` +
      `\input{sections/06d_ridge_eikonal_nonuniform}` を §6 系列に追加.
- [x] xelatex clean 223 pp (+4); 0 undefined refs, 0 errors.
- [x] Fixes: `sec:ccd_nonuniform` → `sec:ccd_metric`,
      `\noindent詳細` → `\noindent 詳細` (XeLaTeX 日本語制御列境界),
      `sec:ccd_gpu` 未定義ラベル削除.

### Phase 3a (CHK-188) — §7 advection / reinit

- [x] `paper/sections/07_0_scheme_per_variable.tex` (new, ≈ 85 行, SP-L §3):
      §7.0 変数別スキーム方針. $\psi$→WENO5/DCCD, $u,v$ bulk→CCD/UCCD6/FCCD,
      界面帯→WENO5/2 次, $p$→face-flux+GFM, $\rho,\mu$→低次. 5 設計原則.
- [x] `paper/sections/07c_fccd_advection.tex` (new, ≈ 220 行, SP-D 全移植):
      §7.3 FCCD 移流. 共通プリミティブ $\mathbf{P}_f = \mathbf{P}_1 - \mathbf{P}_2\mathbf{S}_{\CCD}$,
      面ジェット $\mathcal{J}_f = (\mathbf{P}_f, \mathbf{M}^{\FCCD}, \mathbf{S}_{\CCD}^f)$
      の同一 $\mathbf{q}$ 共有, Option C R$_4$ Hermite 面→節点再構成,
      Option B 保存形面フラックス + スキュー対称形, BF 整合性定理
      (静止状態 $\mathcal{O}(H^4)$ 残差), 壁 BC Option IV Dirichlet 無滑り,
      3 段階移行パス (Stage 1/2/3).
- [x] `paper/sections/07d_cls_stages.tex` (new, ≈ 100 行, SP-L §5-§6):
      §7.5 CLS A→F 6 段階. 3 責務原則 (質量/幾何/補正),
      $\psi\leftrightarrow\phi$ tanh/artanh 対応, TVD-RK3 Shu-Osher,
      narrow-band 再初期化, $\psi(1-\psi)$ 質量補正.
- [x] `paper/sections/07e_viscous_3layer.tex` (new, ≈ 160 行, SP-K §3-§5):
      §7.6 粘性 3 層. $\mu\nabla^2\mathbf{u}$ 禁止証明,
      Layer A (CCD は bulk のみ) / B ($\tau_{xy}$ コーナー) / C (保存形),
      コーナー粘性算術/調和平均, 共有 $\tau_{xy}$ 原則,
      エネルギー恒等式 $\le 0$, 界面帯 CCD 禁止,
      Phi/Psi-gated bulk ショートカット, CN Helmholtz デフェクト補正.
- [x] `paper/main.tex` — 4 `\input` を §7 系列に追加.
- [x] xelatex clean 230 pp (+7); 0 undef refs, 0 undef citations, 0 errors.
- [x] Forward-ref fixes: Olsson2005→OlssonKreiss2005,
      cls_adv_stage→cls_stages, cls_reinit→cls_compression,
      fccd_bf→balanced_force, face_jet→face_jet_def,
      collocate_vs_staggered→collocate_layout.

### Phase 3b (CHK-189) — §8 BF + §9 PPE

- [x] `paper/sections/08_0_bf_failure.tex` (new, ≈ 55 行, SP-J §1):
      BF 連続/離散バランス (eq:bf_continuous_balance/bf_discrete_balance),
      5 失敗モード F-1..F-5 tcolorbox, CHK-172 rising-bubble 適用.
      Label: sec:bf_failure_modes.
- [x] `paper/sections/08_1_bf_seven_principles.tex` (new, ≈ 165 行, SP-J §2):
      P-1 位置一致, P-2 adjoint PPE $D_h^\text{bf} = -(G_h^\text{bf})^T$ + SPD,
      P-3 幾何単一定義, P-4 $\betaf$ 単一定義, P-5 $\kappa$ 帯制限,
      P-6 GFM 界面ジャンプ, P-7 静圧分離, Rhie–Chow 制限.
      Labels: sec:bf_seven_principles, sec:bf_p1_location..p7_separation,
      sec:bf_rhie_chow_restriction.
- [x] `paper/sections/08_2_fccd_bf.tex` (new, ≈ 155 行, SP-A §6 + SP-H §3 + SP-J §3):
      H-01 診断再掲 + FCCD 救済 (残差 $\Ord{\Delta x^2}\to\Ord{\Delta x^4}$),
      面ジェット $\FaceJet{p}$ による BF 構築 ($F^p_f = \betaf p'_f$),
      GFM ジャンプ補正 (Phase 1), 静水圧テスト予測テーブル,
      設計戦略 A/B/C 比較, アンチパターン 8 種 warnbox.
- [x] `paper/sections/08c_pressure_filter.tex` (stub → 85 行, SP-J §4):
      片側 DCCD フィルタの系統的バイアス, 両辺対称整合要件,
      安全性マトリクス, 既定禁止ポリシー.
- [x] `paper/sections/09b_split_ppe.tex` (+190 行, SP-M §5–§8):
      純 FCCD 分相アーキテクチャ, 分相 adjoint pair + SPD,
      GFM ghost jet stitching, 相別ゲージ pin + compatibility,
      pressure-jump formulation, regrid guard.
- [x] `paper/sections/09c_hfe.tex` (+60 行, SP-H §4):
      面ジェット方向 Taylor 状態 $(p^+_f, p^-_f)$ 構築, 風上選択.
- [x] `paper/sections/09d_defect_correction.tex` (+70 行, SP-M §9):
      外殻/内殻剛性分解 $A_H/A_L$, 純 FCCD 収束目標.
- [x] `paper/sections/09e_ppe_bc.tex` (+60 行, SP-C §6 + SP-D §8):
      Option III Neumann 壁, Option IV Dirichlet 値 BC,
      整合性要件 (同一面位置), 周期 FFT/DFT 完全閉式.
- [x] `paper/sections/09_6_gpu_native_fvm.tex` (new, ≈ 165 行, SP-F):
      face-local calculus $L_\text{FVM}(\rho)p = \sum_a D_a A_a G_a p$,
      variable-batched PCR, matrix-free additive preconditioner
      (4-stage truncation CHK-166), D2H discipline, A3 + Phase 1-3 roadmap,
      H-01/A-01 切り分け.
- [x] `paper/main.tex` — §8/§9 `\input` 追加 (08_0/08_1/08_2/09_6).
- [x] Fixes: `\end{center>`→`\end{center}` (09b/09d),
      `\noindent検証`→`\noindent 検証` (XeLaTeX Japanese 境界),
      double superscript `p'^q`→`{p'}^{(q)}` (09e),
      5 未定義前方参照を既存ラベル再マップ.
- [x] xelatex clean 241 pp (+11); 0 undef refs, 0 undef citations, 0 errors;
      SPA/SPC/SPD/SPF/SPH/SPJ/SPM citations resolved.

### Phase 4 (CHK-190) — §10

- [x] `paper/sections/10_full_algorithm.tex` (+180 行, SP-L §6 + §11-§13):
      §10.2 SP-L A-H 8 段階と本稿 Step 1-7 対応. Phase A-H 定義 + Step
      マッピング, 幾何ラグ政策, Phase H 診断セット (6 指標), 演算子分裂
      安全性 (Lie vs Strang), Level 1/2/3 による A-H 具体化.
      Label: sec:algo_sp_l_ah_mapping.
- [x] `paper/sections/10_3_level_selection.tex` (new, ≈ 140 行, SP-I §3):
      §10.3 Level 1/2/3 選択ロジック. CFL 4 制約からの自動トリガー,
      Level 間コスト-精度トレードオフ, Level 1 バリデーション限定,
      Level 2 プロダクション既定, Level 3 極端剛性窓, 物理 → 推奨マトリクス.
- [x] `paper/sections/10_5_pure_fccd_dns.tex` (new, ≈ 205 行, SP-M Phase 1-4):
      §10.5 純 FCCD DNS アーキテクチャ. Phase 1 界面追跡 (Ridge-Eikonal +
      FCCD 保存形), Phase 2 運動量移流 + HFE 風上, Phase 3 粘性 + DC 分離,
      Phase 4 分相 FCCD PPE + GFM 中核, CFD 位置付け (研究 DNS 極限),
      Acceptance Gate G-1..G-5, 実装ロードマップ (SP-M Phase 1-9 対応).
- [x] `paper/sections/10b_dccd_bootstrap.tex` (+10 行, SP-J P-5 annotation):
      適応 DCCD フィルタ末尾に BF 整合性注記. 圧力/毛管圧フィルタ禁止
      ポインタ (§\ref{sec:dccd_pressure_filter_prohibition}),
      $S(\psi)=(2\psi-1)^2$ 界面消失が P-5 の自然実装.
- [x] `paper/main.tex` — §10 系列に 10_3/10_5 inputs 追加.
- [x] Fixes: `sec:verify_ccd_periodic` → `sec:verify_ccd_convergence`,
      §5 \phantomsection\label{sec:level_selection} 削除
      (§10.3 に本定義移動, multiply-defined 解消).
- [x] xelatex clean rebuild 246 pp (+5); 0 undef refs/citations, 0 errors.

---

## 5. Cross-references

### Short papers

Index: [SP_INDEX.md](../../memo/short_paper/SP_INDEX.md).

- [SP-A](../../memo/short_paper/SP-A_face_centered_upwind_ccd.md) — FCCD.
- [SP-B](../../memo/short_paper/SP-B_ridge_eikonal_hybrid.md) — Ridge–Eikonal.
- [SP-C](../../memo/short_paper/SP-C_fccd_matrix_formulation.md) — FCCD matrix.
- [SP-D](../../memo/short_paper/SP-D_fccd_advection.md) — FCCD advection.
- [SP-E](../../memo/short_paper/SP-E_ridge_eikonal_nonuniform_grid.md) — Ridge non-uniform.
- [SP-F](../../memo/short_paper/SP-F_gpu_native_fvm_projection.md) — GPU-native FVM PPE.
- [SP-G](../../memo/short_paper/SP-G_upwind_ccd_pedagogical.md) — DCCD pedagogy.
- [SP-H](../../memo/short_paper/SP-H_fccd_face_jet_fvm_hfe.md) — Face jet.
- [SP-I](../../memo/short_paper/SP-I_time_integration_uccd6_ns.md) — Level-1/2/3 time.
- [SP-J](../../memo/short_paper/SP-J_balanced_force_ccd_fccd_design.md) — BF seven principles.
- [SP-K](../../memo/short_paper/SP-K_viscous_term_ccd_two_phase.md) — Viscous 3-layer.
- [SP-L](../../memo/short_paper/SP-L_advection_cls_body_force_time_integration.md) — CLS 8-phase.
- [SP-M](../../memo/short_paper/SP-M_pure_fccd_phase_separated_ppe_hfe.md) — Pure FCCD DNS.
- [SP-N](../../memo/short_paper/SP-N_uccd6_hyperviscosity.md) — UCCD6 (formerly SP-H).
- [SP-O](../../memo/short_paper/SP-O_paper_rewrite_sp_core.md) — **this plan**.

### Theory wiki

- [WIKI-T-046](../theory/WIKI-T-046.md) — FCCD.
- [WIKI-T-055](../theory/WIKI-T-055.md) — FCCD non-uniform.
- [WIKI-T-062](../theory/WIKI-T-062.md) — UCCD6.
- [WIKI-T-063](../theory/WIKI-T-063.md) — FCCD advection.
- [WIKI-T-068](../theory/WIKI-T-068.md) — Face jet.
- [WIKI-T-069](../theory/WIKI-T-069.md) — Ridge–Eikonal.

### Cross-domain wiki

- [WIKI-X-023](../cross-domain/WIKI-X-023.md) — UCCD6-NS integration.
- [WIKI-X-024](../cross-domain/WIKI-X-024.md) — BF design.
- [WIKI-X-025](../cross-domain/WIKI-X-025.md) — Time integration.
- [WIKI-X-033](../cross-domain/WIKI-X-033.md) — Pure FCCD DNS.

### Experiment wiki

- [WIKI-E-030](../experiment/WIKI-E-030.md) — H-01 diagnosis (CHK-152).

### Ledger

- `docs/02_ACTIVE_LEDGER.md` — CHK-182..190 entries appended per Phase.

---

## 6. Update log

| Date | Event | Commit |
|---|---|---|
| 2026-04-23 | Phase 0 opened: SP-H → SP-N rename, SP_INDEX, SP-O, this dashboard | pending |
| 2026-04-23 | Phase 1a/1b/1c/2a/2b/3a closed: §2 minor + §3.4 Ridge–Eikonal + §4 FCCD/UCCD6 + §5 L1/L2/L3 + §6 non-uniform + §7 advection/viscous | see CHK-183..188 |
| 2026-04-24 | Phase 3b closed (CHK-189): §8 BF failure + 7 principles + FCCD BF + pressure filter; §9 split-PPE +190行 + HFE +60行 + DC +70行 + BC +60行 + GPU-native FVM 165行; 241 pp | db68a70 |
| 2026-04-24 | Phase 4 closed (CHK-190): §10 SP-L A-H 8-phase +180行 + Level 選択 140行 + 純 FCCD DNS 205行 + 10b P-5 annotation; 246 pp | c8b4b28 |
| 2026-04-24 | **§2-§10 SP-core rewrite COMPLETE** — 全 9 phases 完了, 論文 246 pp (+37 pp over pre-rewrite) | — |
