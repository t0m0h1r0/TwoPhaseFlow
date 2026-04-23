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
| 1b | CHK-184 | §3.4 Ridge–Eikonal new subsection | **done** (2026-04-23) | pending |
| 1c | CHK-185 | §4 FCCD/UCCD6/face-jet rewrite | pending | — |
| 2a | CHK-186 | §5 L1/L2/L3 time integration | pending | — |
| 2b | CHK-187 | §6 non-uniform FCCD + ridge | pending | — |
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

- [ ] `paper/sections/04c_dccd_derivation.tex` (new, ≈ 110 lines, SP-G).
- [ ] `paper/sections/04e_fccd.tex` (new, ≈ 180 lines, SP-A+SP-C).
- [ ] `paper/sections/04f_uccd6.tex` (new, ≈ 120 lines, SP-N).
- [ ] `paper/sections/04g_face_jet.tex` (new, ≈ 50 lines, SP-H intro).
- [ ] `paper/sections/04b_ccd_bc.tex` — Option III/IV additions.
- [ ] `paper/sections/04d_dissipative_ccd.tex` — retired (content absorbed
      into 04c).

### Phase 2a (CHK-186) — §5 L1/L2/L3

- [ ] `paper/sections/05_time_integration.tex` — restructured in place.

### Phase 2b (CHK-187) — §6 non-uniform

- [ ] `paper/sections/06c_fccd_nonuniform.tex` (new, ≈ 90 lines, SP-C §5).
- [ ] `paper/sections/06d_ridge_eikonal_nonuniform.tex` (new, ≈ 120 lines, SP-E).

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
