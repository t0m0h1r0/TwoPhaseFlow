# SP Index — Short-Paper Catalogue and Paper-Chapter Mapping

- **Compiled by**: ResearchArchitect
- **Compiled at**: 2026-04-25
- **Purpose**: Canonical dashboard for the SP-A..SP-Z short-paper series.
  Tracks (1) the SP-letter → file mapping (so SP-H renumber events remain
  auditable), and (2) the SP → paper-chapter mapping used by
  [SP-O](SP-O_paper_rewrite_sp_core.md) to drive the §2–§10 rewrite
  (CHK-182..190).
- **Driven by**: [SP-O](SP-O_paper_rewrite_sp_core.md) §3 (SP→Chapter matrix).
  The §-authoritative table in SP-O §3 is the source of truth; this file is the
  ready-reference compression.
- **Wiki twin**: [WIKI-P-013](../../wiki/paper/WIKI-P-013.md) (Phase-level
  progress dashboard).

---

## 1. SP letter → file catalogue

| Letter | File | Topic | Date | Status |
|---|---|---|---|---|
| SP-A | [SP-A_face_centered_upwind_ccd.md](SP-A_face_centered_upwind_ccd.md) | FCCD definition, 4 design principles, H-01 remedy | 2026-04-20 | PROPOSED |
| SP-B | [SP-B_ridge_eikonal_hybrid.md](SP-B_ridge_eikonal_hybrid.md) | Ridge–Eikonal hybrid reinitialisation (topology/metric split, FMM) | 2026-04-20 | PROPOSED |
| SP-C | [SP-C_fccd_matrix_formulation.md](SP-C_fccd_matrix_formulation.md) | FCCD block-matrix form, periodic DFT, non-uniform extension | 2026-04-20 | PROPOSED |
| SP-D | [SP-D_fccd_advection.md](SP-D_fccd_advection.md) | FCCD advection Options B (flux-divergence) / C (Hermite face→node), BF theorem, wall BC | 2026-04-21 | PROPOSED |
| SP-E | [SP-E_ridge_eikonal_nonuniform_grid.md](SP-E_ridge_eikonal_nonuniform_grid.md) | Ridge–Eikonal D1–D4 on non-uniform grids | 2026-04-21 | PROPOSED |
| SP-F | [SP-F_gpu_native_fvm_projection.md](SP-F_gpu_native_fvm_projection.md) | GPU-native FVM PPE (variable-batched PCR, matrix-free MG) | 2026-04-21 | PROPOSED |
| SP-G | [SP-G_upwind_ccd_pedagogical.md](SP-G_upwind_ccd_pedagogical.md) | Pedagogical derivation of DCCD via modified-equation | 2026-04-21 | PROPOSED |
| **SP-H** | [SP-H_fccd_face_jet_fvm_hfe.md](SP-H_fccd_face_jet_fvm_hfe.md) | **Face jet primitive $\mathcal{J}_f(u)=(u_f,u'_f,u''_f)$** (FVM/HFE unifier) | 2026-04-23 | PROPOSED |
| SP-I | [SP-I_time_integration_uccd6_ns.md](SP-I_time_integration_uccd6_ns.md) | Level-1/2/3 time integration for two-phase UCCD6-NS | 2026-04-22 | PROPOSED |
| SP-J | [SP-J_balanced_force_ccd_fccd_design.md](SP-J_balanced_force_ccd_fccd_design.md) | Balanced-force seven principles P-1..P-7, five failure modes F-1..F-5 | 2026-04-22 | PROPOSED |
| SP-K | [SP-K_viscous_term_ccd_two_phase.md](SP-K_viscous_term_ccd_two_phase.md) | Viscous-term 3-layer stress-divergence with defect correction | 2026-04-22 | PROPOSED |
| SP-L | [SP-L_advection_cls_body_force_time_integration.md](SP-L_advection_cls_body_force_time_integration.md) | Per-variable advection policy, CLS A–F stages, 8-phase time step | 2026-04-22 | PROPOSED |
| SP-M | [SP-M_pure_fccd_phase_separated_ppe_hfe.md](SP-M_pure_fccd_phase_separated_ppe_hfe.md) | Pure FCCD two-phase DNS (no FVM, phase-separated PPE, GFM) | 2026-04-23 | PROPOSED |
| **SP-N** | [SP-N_uccd6_hyperviscosity.md](SP-N_uccd6_hyperviscosity.md) | **UCCD6: sixth-order upwind CCD with hyperviscosity** (formerly SP-H) | 2026-04-21 | PROPOSED |
| **SP-O** | [SP-O_paper_rewrite_sp_core.md](SP-O_paper_rewrite_sp_core.md) | **Paper §2–§10 SP-core rewrite plan** (CHK-182..190 executable spec) | 2026-04-23 | ACTIVE |
| **SP-P** | [SP-P_face_canonical_projection_survey.md](SP-P_face_canonical_projection_survey.md) | **Face-canonical variable-density projection survey + ch13 PoC ladder** | 2026-04-24 | ACTIVE |
| **SP-Q** | [SP-Q_buoyancy_driven_predictor_assembly.md](SP-Q_buoyancy_driven_predictor_assembly.md) | **Buoyancy-driven predictor assembly theory for ch13 CN intermediate-state failure** | 2026-04-25 | ACTIVE |
| **SP-R** | [SP-R_interface_band_predictor_closure_derivation.md](SP-R_interface_band_predictor_closure_derivation.md) | **NS × LS × CFD derivation of interface-band predictor closure and buoyancy-aware assembly** | 2026-04-25 | ACTIVE |
| **SP-S** | [SP-S_buoyancy_predictor_redesign_theorem.md](SP-S_buoyancy_predictor_redesign_theorem.md) | **Redesign theorem and minimal admissible algorithm for buoyancy-aware predictor assembly** | 2026-04-25 | ACTIVE |
| **SP-T** | [SP-T_stage_split_buoyancy_predictor_redesign.md](SP-T_stage_split_buoyancy_predictor_redesign.md) | **Stage-split redesign: vertical assembly repair + `V(u_pred)`-stage horizontal coupling** | 2026-04-25 | ACTIVE |
| **SP-U** | [SP-U_buoyancy_predictor_well_balanced_foundation.md](SP-U_buoyancy_predictor_well_balanced_foundation.md) | **Literature-backed mathematical foundation for a pressure-robust, well-balanced buoyancy predictor** | 2026-04-25 | ACTIVE |
| **SP-V** | [SP-V_discrete_buoyancy_predictor_operator_spec.md](SP-V_discrete_buoyancy_predictor_operator_spec.md) | **Discrete operator contract for stage-split buoyancy predictor assembly and `V(u_pred)` coupling** | 2026-04-25 | ACTIVE |
| **SP-W** | [SP-W_phase_separated_projection_closure.md](SP-W_phase_separated_projection_closure.md) | **Phase-separated FCCD projection closure: PPE / residual / corrector face coefficient consistency** | 2026-04-25 | ACTIVE |
| **SP-X** | [SP-X_projection_closure_trial_synthesis.md](SP-X_projection_closure_trial_synthesis.md) | **Trial synthesis and theory of the clean-main phase-separated projection closure** | 2026-04-25 | ACTIVE |
| **SP-Y** | [SP-Y_cfl_time_integration_policy.md](SP-Y_cfl_time_integration_policy.md) | **CFL and time-integration policy for capillary/two-phase NS runs** | 2026-04-25 | ACTIVE |
| **SP-Z** | [SP-Z_rising_bubble_buoyancy_fmm_closure.md](SP-Z_rising_bubble_buoyancy_fmm_closure.md) | **Rising-bubble buoyancy/FMM closure validated by ch13 t=0.5 run** | 2026-04-25 | ACTIVE |

**Letter collision history**:
- 2026-04-21: `SP-H_uccd6_hyperviscosity.md` created (UCCD6 short paper).
- 2026-04-23: New face-jet short paper took the `SP-H` slot as
  `SP-H_fccd_face_jet_fvm_hfe.md`. The older UCCD6 note was renumbered to
  **SP-N** (`SP-N_uccd6_hyperviscosity.md`) to keep the one-letter-one-paper
  convention. All in-repo back-references (SP-I, WIKI-T-062, WIKI-X-023,
  `src/twophase/ccd/uccd6.py`) were updated at the same commit.

---

## 2. SP → paper-chapter mapping (summary)

Canonical source: [SP-O §3](SP-O_paper_rewrite_sp_core.md#3-sp--chapter-mapping).
This table is the pinned one-page compression.

| Chapter | Primary SPs (core) | Secondary SPs (supporting) | Rewrite type |
|---|---|---|---|
| §2 Governing equations | — | SP-J §1 (BF failure motivation) | minor |
| §3 Level-set / CLS | **SP-B**, **SP-E** | SP-L §3 (per-variable policy) | major addition |
| §4 CCD / FCCD / UCCD6 | **SP-G**, **SP-A**, **SP-C**, **SP-N** | SP-H (face-jet primitive) | substantial rewrite |
| §5 Time integration | **SP-I** | SP-N (CN + UCCD6) | reorganised |
| §6 Non-uniform grids | **SP-C §5**, **SP-E** | — | major addition |
| §7 Advection / reinit | **SP-D**, **SP-L**, **SP-K** | SP-H (face-jet HFE) | full rewrite |
| §8 Pressure/velocity coupling | **SP-J**, **SP-A** | SP-H (face-jet FVM projection) | substantial rewrite |
| §9 PPE | **SP-M**, **SP-F**, **SP-J §4** | SP-H (face-jet PPE flux) | substantial rewrite |
| §10 Complete algorithm | **SP-L**, **SP-I**, **SP-M** | SP-H (face-jet unified pipeline) | full rewrite |

---

## 3. Phase → CHK → SP cross-reference

| Phase | CHK | Deliverables | Primary SPs |
|---|---|---|---|
| 0 | CHK-182 | SP-H/N renumber, SP_INDEX, **SP-O**, **WIKI-P-013**, preamble macros | — (housekeeping) |
| 1a | CHK-183 | §2 minor + §1.5 SP index block | SP-J §1 |
| 1b | CHK-184 | §3.4 Ridge–Eikonal (new) | SP-B, SP-E |
| 1c | CHK-185 | §4 DCCD/FCCD/UCCD6 full rewrite | SP-G, SP-A, SP-C, SP-N, SP-H |
| 2a | CHK-186 | §5 Level-1/2/3 time integration | SP-I |
| 2b | CHK-187 | §6 non-uniform FCCD + Ridge–Eikonal | SP-C §5, SP-E |
| 3a | CHK-188 | §7 per-variable + FCCD advection + viscous 3-layer | SP-D, SP-L, SP-K, SP-H |
| 3b | CHK-189 | §8 BF + §9 phase-separated FCCD PPE + GPU-native | SP-J, SP-M, SP-F, SP-H |
| 4 | CHK-190 | §10 8-phase + Level selection + pure FCCD DNS | SP-L, SP-I, SP-M |

Progress tracking lives in [WIKI-P-013](../../wiki/paper/WIKI-P-013.md) and
`docs/02_ACTIVE_LEDGER.md`.

---

## 4. Convention

- **One letter, one paper**: never reuse a letter after retirement. The SP-H
  collision resolution of 2026-04-23 (SP-H_uccd6 → SP-N) is the canonical
  template for future collisions.
- **Status lifecycle**: `PROPOSED` (research memo, no binding on code) →
  `ACTIVE` (driving a CHK) → `INTEGRATED` (equations landed in the paper).
- **Back-reference hygiene**: when a letter is renumbered, update all
  repo-internal references in the same commit. Use `grep -rn "SP-<old>"` on
  `docs/`, `paper/`, and `src/` to audit.
