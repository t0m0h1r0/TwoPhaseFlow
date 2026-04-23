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

Current Phase: **0 (CHK-182, in progress)**.

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
| 2b | CHK-187 | §6 non-uniform FCCD + ridge | **done** (2026-04-23) | (pending commit) |
| 3a | CHK-188 | §7 per-variable + FCCD advection + viscous 3-layer | pending | — |
| 3b | CHK-189 | §8 BF + §9 FCCD PPE + GPU-native | pending | — |
| 4 | CHK-190 | §10 8-phase + Level selection + pure-FCCD DNS | pending | — |

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

- [ ] `paper/sections/07_0_scheme_per_variable.tex` (new, ≈ 60 lines, SP-L §3).
- [ ] `paper/sections/07c_fccd_advection.tex` (new, ≈ 220 lines, SP-D).
- [ ] `paper/sections/07d_cls_stages.tex` (new, ≈ 80 lines, SP-L §5).
- [ ] `paper/sections/07e_viscous_3layer.tex` (new, ≈ 140 lines, SP-K).

### Phase 3b (CHK-189) — §8 BF + §9 PPE

- [ ] `paper/sections/08_0_bf_failure.tex` (new, ≈ 45 lines, SP-J §1).
- [ ] `paper/sections/08_1_bf_seven_principles.tex` (new, ≈ 160 lines, SP-J §2).
- [ ] `paper/sections/08_2_fccd_bf.tex` (new, ≈ 130 lines, SP-A+SP-H+SP-J §3).
- [ ] `paper/sections/08c_pressure_filter.tex` — expanded from stub (SP-J P-5).
- [ ] `paper/sections/09b_split_ppe.tex` — +160 lines (SP-M §5–§8).
- [ ] `paper/sections/09c_hfe.tex` — +30 lines (SP-H §4).
- [ ] `paper/sections/09d_defect_correction.tex` — +20 lines (SP-M §9).
- [ ] `paper/sections/09e_ppe_bc.tex` — Option III/IV explicit.
- [ ] `paper/sections/09_6_gpu_native_fvm.tex` (new, ≈ 130 lines, SP-F).

### Phase 4 (CHK-190) — §10

- [ ] `paper/sections/10_full_algorithm.tex` — §10.2 expanded to 8 phases
      A–H (SP-L §6).
- [ ] `paper/sections/10_3_level_selection.tex` (new, ≈ 80 lines, SP-I §3).
- [ ] `paper/sections/10_5_pure_fccd_dns.tex` (new, ≈ 150 lines, SP-M).

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
| — | Phase 1a–4 | to follow |
