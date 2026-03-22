# PROJECT CHECKLIST

> **How to use:**
> - `[x]` = done / verified clean
> - `[ ]` = not yet done
> - `[~]` = partially done / in progress
> - `[!]` = issue found, needs attention
>
> Update this file whenever a workflow produces a new verdict. Cross-reference `docs/ACTIVE_STATE.md` for full status text.

---

## 1. Paper — Mathematical Audit (MATH_VERIFY / PAPER_EDITOR sweeps)

### §1–§5 (prior sessions)

| Section | File | Last sweep | Type | Status | Notes |
|---------|------|-----------|------|--------|-------|
| §1 Introduction | `01_introduction.tex` | 2026-03-22 | CRITIC+EDITOR | `[x]` SAFE | WENO5→Dissipative CCD global sweep; 6 occurrences fixed |
| §2 Governing eqs | `02_governing.tex` | sweep 28 + 2026-03-21 | EDITOR+MATH_VERIFY | `[x]` | 球状液滴→円形液滴 fixed; One-Fluid / CSF verified |
| §3 Level Set | `03_levelset.tex` | sweep 20 + 2026-03-22 | EDITOR+MATH_VERIFY | `[x]` | CLS fixed-point verified; "WENO5 打ち切り誤差"→Dissipative CCD |
| §4 CCD method | `04_ccd.tex` + `04b_ccd_bc.tex` + `04c_ccd_extensions.tex` + `04d_dissipative_ccd.tex` | 2026-03-22 | CRITIC+EDITOR | `[x]` | ε_d=0.05 → H(π)=0.80 added; A_L/A_R signs verified |
| §5 CLS advection | `05_advection.tex` | 2026-03-22 | CRITIC+EDITOR | `[x]` | New chapter (merged from old §4 time_integration). Dissipative CCD scheme; mass conservation O(h⁵Δt) step clarified; ψ clamp note |

### §6–§11 + Appendices (sweep 29, 2026-03-21)

| Section | File | Status | Notes |
|---------|------|--------|-------|
| §6 Grid generation | `06_grid.tex` | `[x]` FIXED | MATH_VERIFY 2026-03-22: PAPER_ERROR ω(0)=α → ω(0)=1+(α−1)/(ε_g√π) fixed; density function formula, transforms, metric code all VERIFIED; 10 targets total |
| §7 Collocated | `07_collocate.tex` | `[~]` UPDATED | EDITOR sweep 30+31 (2026-03-22): eq:bf_operator_mismatch fixed (O(h²) not O(h⁶)−O(h²)); blow-up positive-feedback mechanism added; warnbox κ item demoted to "推奨"; warnbox item 3 updated to eq:rc-face-balanced; sec:rc_balanced_force rewrote with full quantity definitions + code-gap warnbox + face/cell-center cancellation logic; algbox "機械精度" → O(h²) CSF floor; appendix derivation expanded to show equilibrium cancellation. Build pending. |
| §8 Pressure / IPC | `08_pressure.tex` | `[x]` SAFE | — |
| §8b CCD-Poisson | `08b_ccd_poisson.tex` | `[x]` SAFE | Spectral radius formula 9.6≠3.43 clarified |
| §8c PPE verification | `08c_ppe_verification.tex` | `[x]` SAFE | — |
| §8d PPE pseudo-time | `08d_ppe_pseudotime.tex` | `[x]` UPDATED | CRITIC 23 + EDITOR sweep 35 (2026-03-23): 4 FATAL + 9 minor fixes; ADI eq corrected (Δτ/2 q_h), C_τ unified, 5 labels added, table row added, notation unified |
| §9 Full algorithm | `09_full_algorithm.tex` | `[x]` SAFE | — |
| §10 Verification | `10_verification.tex` | `[x]` SAFE | Pre-asymptotic O(h⁴) note added |
| §11 Conclusion | `11_conclusion.tex` | `[x]` SAFE | — |
| App: interface proofs | `appendix_interface.tex` | `[x]` SAFE | 5 sections: Newton conv., One-Fluid, μ interp., δ_s, CLS fixed-pt |
| App: CCD coefficients | `appendix_ccd_coef.tex` | `[x]` SAFE | Eq-I/II interior + BC derivations |
| App: CCD impl | `appendix_ccd_impl.tex` | `[x]` SAFE | Ghost-cell, mixed deriv., elliptic solver |
| App: numerics solver | `appendix_numerics_solver.tex` | `[x]` SAFE | Δτ derivation + checkerboard + capillary CFL (A15 text fix) |
| App: numerics schemes | `appendix_numerics_schemes.tex` | `[x]` SAFE | ALE, Rhie-Chow, Godunov LS |

---

## 2. Code–Paper Consistency — Verification Register

Canonical audit log (single source of truth; moved from `13_MATH_VERIFY.md`). Append new verifications here.

| Target | Paper location | Code file | Date | Verdict | Notes |
|--------|---------------|-----------|------|---------|-------|
| Eq-I coefficients (α₁, a₁, b₁) | `05_ccd.tex` eq:CCD_TE | `ccd_solver.py:51-53` | 2026-03-20 | ✅ VERIFIED | TE = −1/7! |
| Eq-II coefficients (β₂, a₂, b₂) | `05_ccd.tex` eq:coef_CCD | `ccd_solver.py:55-57` | 2026-03-20 | ✅ VERIFIED | TE = −2/8! |
| A_L, A_R (2,1) entries | `05b_ccd_bc_matrix.tex` l.147 | `ccd_solver.py:186-189` | 2026-03-20 | ✅ FIXED | PAPER_ERROR (KL-01); A_L(2,1)=−9/(8h), A_R(2,1)=+9/(8h) |
| Left boundary Eq-I (O(h⁵)) | `05b_ccd_bc_matrix.tex` eq:bc_left | `ccd_solver.py:299` | 2026-03-20 | ✅ VERIFIED | α=3/2 unique; h⁴ coefficient cancels |
| Left boundary Eq-II (paper) | `appendix_ccd_coef.tex` eq:bcII_left | — | 2026-03-20 | ✅ VERIFIED | O(h²) one-sided formula confirmed |
| Left boundary Eq-II (code) | `appendix_ccd_coef.tex` | `ccd_solver.py:303` | 2026-03-21 | ✅ STALE RESOLVED | Code uses [2,−5,4,−1]/h² = paper O(h²) formula; prior discrepancy was stale |
| TE_I = −1/7! | `05_ccd.tex`, `appendix_ccd_coef.tex` | — | 2026-03-20 | ✅ VERIFIED | −1/5040 exact |
| TE_II = −2/8! | `05_ccd.tex`, `appendix_ccd_coef.tex` | — | 2026-03-20 | ✅ VERIFIED | −1/20160 exact |
| Boundary Eq-I O(h⁵) accuracy | `05b_ccd_bc_matrix.tex` | — | 2026-03-20 | ✅ VERIFIED | h⁴ coefficient cancels |
| PPE pseudo-time γ(t) derivation | `08_pressure.tex` / `appendix_numerics_solver.tex` | `ppe_solver_pseudotime.py` | 2026-03-21 | ✅ VERIFIED | γ(t)=(1+t²)/(1+t)²; t*=1; Δτ_opt=0.58h²/a_max |
| Variable-density PPE product rule | `08_pressure.tex` | `ppe_solver_pseudotime.py` | 2026-03-21 | ✅ VERIFIED | (1/ρ)∇²p − (∇ρ/ρ²)·∇p ✓ |
| Harmonic mean face coefficient a_f | `appendix_numerics_solver.tex` | `ppe_solver_pseudotime.py` | 2026-03-21 | ✅ VERIFIED | 2/(ρ_L+ρ_R) from series resistance ✓ |
| μ arithmetic mean derivation | `appendix_interface.tex` | — | 2026-03-21 | ✅ VERIFIED | Linear ψ → volume avg = arithmetic mean ✓ |
| CLS fixed-point H_ε(φ) | `appendix_interface.tex` | `reinitialize.py` | 2026-03-21 | ✅ VERIFIED | LHS=RHS=(1/ε)(1−2ψ)ψ(1−ψ) ✓ |
| TVD-RK3 Shu-Osher coefficients | `09_full_algorithm.tex` | `tvd_rk3.py` | 2026-03-21 | ✅ VERIFIED | Stage coefficients (1,1),(3/4,1/4,1/4),(1/3,2/3,2/3) ✓ |
| Capillary CFL derivation | `appendix_numerics_solver.tex` | `cfl.py` | 2026-03-21 | ✅ VERIFIED (text fix) | Formula OK; "保守的に" wording corrected (KL-07) |
| ‖∇ψ‖≈δ_s error O(ε²) | `appendix_interface.tex` | — | 2026-03-21 | ✅ VERIFIED | Odd-function cancellation; ∫t²δ_ε dt = π²ε²/3 ✓ |
| Balanced-Force O(h⁶) argument | `07_collocate.tex` | — | 2026-03-21 | ✅ VERIFIED (fix) | Conclusion correct; Leibniz algebra fixed (KL-04) |
| CCD spectral radius 3.43/h² | `08b_ccd_poisson.tex` | — | 2026-03-21 | ✅ VERIFIED (fix) | Self-consistent with Δτ_opt; 9.6/h² is Nyquist bound (KL-05) |
| Kronecker product 2D operator eq:L_CCD_2d_kron | `appendix_ccd_impl.tex` app:ccd_kronecker | `ppe_solver_pseudotime.py:267-284` | 2026-03-21 | ✅ VERIFIED | C-order k=i·Ny+j; kron(D2x,I_Ny)+kron(I_Nx,D2y) ✓ (KL-08) |
| PPE solver strategy (LGMRES + LU fallback) | `appendix_ccd_impl.tex` app:ccd_lu_direct | `ppe_solver_pseudotime.py:solve()` | 2026-03-21 | ✅ VERIFIED | LGMRES primary, spsolve fallback on info≠0 (KL-09) |
| Rhie-Chow ρⁿ⁺¹ face coefficient | `07_collocate.tex:164,171` | `rhie_chow.py:119-124` | 2026-03-21 | ✅ VERIFIED | 2/(ρ_P^{n+1}+ρ_E^{n+1}) harmonic mean ✓ |
| WENO5 β₀,β₁,β₂ (Jiang-Shu) | `04_time_integration.tex:122-126` | `advection.py:246-248` | 2026-03-21 | ✅ VERIFIED | (13/12)(·)²+(1/4)(·)²; d₀=1/10,d₁=3/5,d₂=3/10; ε=1e-6 ✓ |
| CFL advection + viscous conditions | `04b_time_schemes.tex:271-286` | `cfl.py:100-113` | 2026-03-21 | ✅ VERIFIED | Advection CFL ✓; viscous CFL safety factor conservative ✓ |
| CSF curvature κ = −(…)/‖∇φ‖³ | `02c_nondim_curvature.tex:281-288` | `curvature.py:97-111` | 2026-03-21 | ✅ VERIFIED | Rederived from ∇·(∇φ/‖∇φ‖) ✓ |
| Dissipative CCD |g(ξ)|²>1 instability proof | `05_advection.tex` eq:ccd_adv_instability | `advection.py` | 2026-03-22 | ✅ VERIFIED | Von Neumann analysis: |g|²=1+σ²[k*(ξ)/k]²>1 ∀ξ>0; H(π;0.05)=0.80; ε_d=0.05 hardcoded |
| Dissipative CCD filter sum=0 (periodic) | `05_advection.tex` mass conservation | `advection.py` | 2026-03-22 | ✅ VERIFIED | Shift-symmetry ⟹ Σ(f'_{i+1}−2f'_i+f'_{i-1})=0; O(h⁵Δt) per step; implemented in DissipativeCCDAdvection._rhs |
| Rhie-Chow FVM div at wall node N_ax | §7 / appendix RC | `rhie_chow.py:_flux_divergence_1d` | 2026-03-22 | ✅ FIXED (BUG) | div[N_ax]=(face_{N_ax+1}−face_{N_ax})/h = −flux[N_ax]/h; padding 0 treated interior face N_ax as wall face (WRONG) |
| PPE gauge pin — symmetry invariance | §8 / appendix FVM PPE | `ppe_builder.py`, `ppe_solver*.py` | 2026-03-22 | ✅ FIXED (BUG) | Corner pin (0,0) breaks x-flip/y-flip symmetry → spurious antisymmetric ∇p; center node (N/2,N/2) is invariant under all square-domain symmetries |
| `L_CCD^ρ` product-rule derivation | `ppe_solver_pseudotime.py:305-308` | same | 2026-03-22 | ✅ VERIFIED | (1/ρ)(D2x+D2y)−(Dρx/ρ²)D1x−(Dρy/ρ²)D1y matches ∇·(1/ρ∇p) product rule exactly |
| Kronecker C-order + axis=1 transpose | `ppe_solver_pseudotime.py:291-294,259-260` | same | 2026-03-22 | ✅ VERIFIED | kron(D2x,I_y)+kron(I_x,D2y) correct for C-order p.ravel(); axis=1 needs d1.T (KL-08 extension) |
| `_enforce_neumann` index range | `velocity_corrector.py:93-98` | same | 2026-03-22 | ✅ VERIFIED | sl_lo[ax]=0, sl_hi[ax]=-1 zeroes correct wall-normal boundary nodes |
| Corrector divergence-free claim | `09_full_algorithm.tex:246` | `velocity_corrector.py` | 2026-03-22 | ✅ FIXED (LOGICAL_GAP) | D_CCD·u^{n+1}=O(h²)≠0; velocity satisfies ∇^RC·u^{n+1}=0; paper now states RC-sense (KL-10) |
| `compute_residual()` pin exclusion | `ppe_solver_pseudotime.py:230` | same | 2026-03-22 | ✅ FIXED (CODE_BUG) | Was excluding corner node 0; now excludes center pin_dof=(N//2)*Ny+(N//2) (KL-11) |
| Capillary CFL safety factor | `appendix_numerics_solver.tex` eq:dt_sigma | `cfl.py:117` | 2026-03-22 | ✅ FIXED (BUG) | dt=min(dt, dt_sigma) operated at marginal stability limit; fixed to dt=min(dt, cfl·dt_sigma) consistent with convective/viscous constraints |
| δ*(φ) normalization ∫δ*dφ=1 | `06_grid.tex` eq:grid_delta | `grid.py:122` | 2026-03-22 | ✅ VERIFIED | ∫exp(−φ²/ε_g²)/(ε_g√π)dφ = 1 exact ✓ |
| ω(0) = α claim | `06_grid.tex` パラメータ選択指針 | — | 2026-03-22 | ✅ FIXED (PAPER_ERROR) | ω(0)=1+(α−1)/(ε_g√π)≠α; corrected to exact formula in paper |
| eq:transform_1st_correct ∂f/∂x=J·∂f/∂ξ | `06_grid.tex` | `grid.py:183-185` | 2026-03-22 | ✅ VERIFIED | Standard chain rule; J=∂ξ/∂x ✓ |
| eq:transform_2nd_correct ∂²f/∂x² | `06_grid.tex` | `grid.py:154-157` | 2026-03-22 | ✅ VERIFIED | ∂/∂x(J·∂f/∂ξ)=J²·∂²f/∂ξ²+J·(∂J/∂ξ)·∂f/∂ξ ✓ |
| J=1/d1_raw, dJ=−d2_raw/d1_raw² | `06_grid.tex` Step 5 | `grid.py:179-180` | 2026-03-22 | ✅ VERIFIED | Implicit differentiation of J=1/(dx/dξ) ✓ |
| differentiate_raw axis embedding | — | `ccd_solver.py` | 2026-03-22 | ✅ VERIFIED | shape=[1]*ndim; shape[axis]=-1 broadcasts 1D coords to correct axis ✓ |
| MMS thresholds ≥3.5 (J), ≥2.5 (∂J/∂ξ) | ARCH §6 | `test_grid.py:146,196` | 2026-03-22 | ✅ VERIFIED | Matches CCD boundary accuracy for d1/d2 ✓ |
| min|φ| marginal (§6 2D algo) | `06_grid.tex` 2D tensor-product | `grid.py:119` | 2026-03-22 | ✅ VERIFIED | np.min(np.abs(phi), axis=other) = closest interface approach ✓ |

---

## 3. LaTeX Build

- `[~]` `xelatex` (latexmk) — last confirmed clean 2026-03-21 (119 pages); EDITOR sweep 33 edits pending compile verification
- `[x]` CRITIC pass 24 + EDITOR sweep 37 (2026-03-23) — `08d`: FATAL-1 sweep≠欠陥補正（別手法書き直し）; FATAL-2 eq:residual増分式修正; GAP-1 近似解明記; GAP-2 LTS均等収束数式; IMPL-1 未実装注記; MINOR-1 result:etol_criterionリネーム. `07`: STRUCT-1 重複結論削除
- `[x]` CRITIC pass 23 + EDITOR sweep 35 (2026-03-23) — `08d_ppe_pseudotime.tex`: ADI Δτ/2 fix (FATAL-1), tcolorbox `\eqref` fix (FATAL-2), C_τ三重矛盾解消 (FATAL-3), 安定条件→最適収束域 (FATAL-4), 5 labels追加, tab:ppe_methods 欠陥補正行追加, 変数凍結節移動
- `[x]` EDITOR sweep 36 (2026-03-23) — `07_collocate.tex`: BF code-alignment confirmation (3 CCD sites verified) + stability-conclusion sentence in warnbox
- `[x]` EDITOR sweep 34 (2026-03-23) — `08d_ppe_pseudotime.tex` 3 new subsubsections: variable freeze, defect correction (eq:defect_correction_split/linear), LTS (eq:dtau_lts)
- `[x]` CRITIC pass 22 + EDITOR sweep 33 (2026-03-22) — 全体構造・用語統一: 08c追加, FATAL-3 label rename, ARCHITECTURE.md修正, Rhie--Chow統一, Balanced-Force統一, 05分割(→05b/05c), 08分割(→08d)
- `[x]` CRITIC pass 20 (2026-03-22) — WENO5→Dissipative CCD global sweep + 4 clarity fixes
- `[x]` EDITOR sweep 32 (2026-03-22) — §7 Balanced-Force: 12 issues

---

## 4. Code Test Suite

- `[x]` `pytest src/twophase/tests/` — **53 passed, 2 skipped** (as of 2026-03-22; +14 from non-uniform grid + dissipative CCD tests)
- `[x]` **CODE-PAPER GAP CLOSED:** `DissipativeCCDAdvection(ILevelSetAdvection)` added to `levelset/advection.py` (§5 alg:dccd_adv). `NumericsConfig.advection_scheme = "dissipative_ccd"` (default); `"weno5"` selectable. `SimulationBuilder` updated. 2 MMS tests added (spatial O(h²) ≥ 1.8, full method ≥ 1.8).
- `[x]` **config_loader YAML round-trip fixed:** `advection_scheme` added to load/`_known`/dump in `config_loader.py`. Previously silently dropped on round-trip and triggered unknown-key warning.
- `[x]` **ε_factor < 1.2 safety warning:** `UserWarning` in `NumericsConfig.__post_init__` for `epsilon_factor < 1.2` + `advection_scheme="dissipative_ccd"` (§5 warn:adv_risks(B)).
- `[x]` **test_config.py added:** 6 tests — scheme validation (valid/invalid), ε_factor warning (positive/negative/safe), YAML round-trip, unknown-key suppression.
- `[x]` **Dead code removed (refactor):** `_pad_zero` alias (`advection.py`), `Optional` unused import (`config_loader.py`), `TYPE_CHECKING` unused import (`_core.py`).
- `[x]` **Symmetry-breaking root causes fixed (2026-03-22):** (1) `rhie_chow.py` wall node FVM div formula corrected; (2) PPE pin moved to center node (N/2,N/2); (3) capillary CFL safety factor applied. Machine-precision symmetry confirmed at sub-capillary-CFL timestep.
- `[!]` Benchmark at N=128 — stationary_droplet NaN for all N; PPE fails at 1000:1 density ratio (see §5 action item)
- `[ ]` GPU backend (CuPy) compatibility check
- `[ ]` 3D cases
- `[ ]` VTK output writer (`io/`)

---

## 5. Open Action Items

### Paper / Documentation

- `[x]` Boundary Eq-II discrepancy RESOLVED (2026-03-21)
- `[x]` Formal MATH_VERIFY for §§1–4 — SAFE (2026-03-21)
- `[x]` Formal MATH_VERIFY for Rhie-Chow, WENO5, TVD-RK3, Capillary CFL, CSF curvature — all VERIFIED (2026-03-21)
- `[x]` CRITIC pass 19 (2026-03-21) — new appendix sections all SAFE

### Code

- `[x]` **Dissipative CCD advection** — `DissipativeCCDAdvection` implemented + registered + tested (2026-03-22).
- `[!]` N=128 benchmark — BLOCKED: stationary_droplet NaN (PPE diverges for ρ ratio 1000:1); await user direction (A/B/C)
- `[ ]` GPU (CuPy) backend verification
- `[ ]` 3D implementation
- `[ ]` VTK output writer

---

## 6. Workflow Quick Reference

| Task | Use |
|------|-----|
| Re-derive / audit equation | `docs/13_MATH_VERIFY.md` |
| Fix paper per reviewer comments | `docs/11_PAPER_EDITOR.md` |
| Critical review of whole paper | `docs/10_PAPER_REVIEW.md` |
| Fix LaTeX syntax / build errors | `docs/12_LATEX_ENGINE.md` |
| Diagnose test failures (post-hoc verdict) | `docs/03_CODE_VERIFY.md` |
| Active debugging (staged experiments + patches) | `docs/05_CODE_DEBUG.md` |
| Add new code features | `docs/02_CODE_DEVELOP.md` |
| Refactor code | `docs/04_CODE_REFACTOR.md` |

---
