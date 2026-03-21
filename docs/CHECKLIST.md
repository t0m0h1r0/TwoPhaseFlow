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
| §1 Introduction | `01_intro.tex` | 2026-03-21 | MATH_VERIFY | `[x]` SAFE | Prose only; no derivation target |
| §2 Governing eqs | `02_governing.tex` | sweep 28 + 2026-03-21 | EDITOR+MATH_VERIFY | `[x]` | 球状液滴→円形液滴 fixed; One-Fluid / CSF verified |
| §3 Level Set | `03_levelset.tex` | sweep 28 + 2026-03-21 | EDITOR+MATH_VERIFY | `[x]` | CLS fixed-point verified; reinitialization Δτ noted |
| §4 Time integration | `04_time_integration.tex` | 2026-03-21 | MATH_VERIFY | `[x]` SAFE | WENO5 β+weights ✓; TVD-RK3 ✓; CFL ✓ |
| §5 CCD method | `05_ccd.tex` + `05b_ccd_bc_matrix.tex` | 2026-03-20 | MATH_VERIFY | `[x]` | A_L/A_R (2,1) sign error found and fixed |

### §6–§11 + Appendices (sweep 29, 2026-03-21)

| Section | File | Status | Notes |
|---------|------|--------|-------|
| §6 Grid generation | `06_grid.tex` | `[x]` SAFE | Comment fix: "台形則"→"矩形則（前進型）" |
| §7 Collocated | `07_collocate.tex` | `[x]` SAFE | Balanced-Force Leibniz algebra fix |
| §8 Pressure / IPC | `08_pressure.tex` | `[x]` SAFE | — |
| §8b CCD-Poisson | `08b_ccd_poisson.tex` | `[x]` SAFE | Spectral radius formula 9.6≠3.43 clarified |
| §8c PPE verification | `08c_ppe_verification.tex` | `[x]` SAFE | — |
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

---

## 3. LaTeX Build

- `[x]` `pdflatex` clean — 0 errors, 0 undefined references (last confirmed: sweep 29, 2026-03-21)
- `[x]` Page count stable: **116 pages**
- `[!]` Re-build needed — `appendix_ccd_impl.tex` had structural additions (app:ccd_kronecker, app:ccd_lu_direct rewrite) in 2026-03-21 session; run `pdflatex` to confirm no new undefined references

---

## 4. Code Test Suite

- `[x]` `pytest src/twophase/tests/` — **31 tests passing** (as of 2026-03-21)
- `[ ]` Benchmark at N=128 (higher-resolution confirmation)
- `[ ]` GPU backend (CuPy) compatibility check
- `[ ]` 3D cases
- `[ ]` VTK output writer (`io/`)

---

## 5. Open Action Items

### Paper / Documentation

- `[x]` Boundary Eq-II discrepancy RESOLVED (2026-03-21)
- `[x]` Formal MATH_VERIFY for §§1–4 — SAFE (2026-03-21)
- `[x]` Formal MATH_VERIFY for Rhie-Chow, WENO5, TVD-RK3, Capillary CFL, CSF curvature — all VERIFIED (2026-03-21)
- `[ ]` Next CRITIC pass (pass 19) if major new content is added

### Code

- `[ ]` N=128 benchmark runs and comparison to reference values
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
| Diagnose test failures | `docs/03_CODE_VERIFY.md` |
| Add new code features | `docs/02_CODE_DEVELOP.md` |
| Refactor code | `docs/04_CODE_REFACTOR.md` |

---
