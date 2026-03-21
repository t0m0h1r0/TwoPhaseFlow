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
| §1 Introduction | `01_intro.tex` | sweep ≤27 | CRITIC/EDITOR | `[~]` no formal MATH_VERIFY | — |
| §2 Governing eqs | `02_governing.tex` | sweep 28 | EDITOR | `[x]` | 球状液滴→円形液滴（2次元）fixed |
| §3 Level Set | `03_levelset.tex` | sweep 28 | EDITOR | `[x]` | CLS volume-conservation formula fixed |
| §4 Time integration | `04_time_integration.tex` | sweep ≤27 | CRITIC/EDITOR | `[~]` no formal MATH_VERIFY | — |
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

## 2. Code–Paper Consistency (MATH_VERIFY register)

| Algorithm | Code file | Paper ref | Status | Notes |
|-----------|-----------|-----------|--------|-------|
| CCD Eq-I coefficients (α₁, a₁, b₁) | `ccd_solver.py:51-53` | `05_ccd.tex` | `[x]` VERIFIED | TE = −1/7! |
| CCD Eq-II coefficients (β₂, a₂, b₂) | `ccd_solver.py:55-57` | `05_ccd.tex` | `[x]` VERIFIED | TE = −2/8! |
| A_L, A_R block matrices | `ccd_solver.py:186-189` | `05b_ccd_bc_matrix.tex` | `[x]` FIXED | A_L(2,1)=−9/(8h), A_R(2,1)=+9/(8h) |
| Boundary Eq-I (O(h⁵)) | `ccd_solver.py:299` | `appendix_ccd_coef.tex` | `[x]` VERIFIED | α=3/2 unique O(h⁵) solution |
| Boundary Eq-II (paper O(h²)) | `appendix_ccd_coef.tex` | `appendix_ccd_coef.tex` | `[x]` VERIFIED | — |
| Boundary Eq-II (code coupled) | `ccd_solver.py:303` | `appendix_ccd_coef.tex` | `[x]` STALE RESOLVED (2026-03-21) | Code uses `[2,−5,4,−1]/h²` = paper O(h²) formula; prior entry was stale |
| PPE pseudo-time convergence | `ppe_solver_pseudotime.py` | `08_pressure.tex` / `appendix_numerics_solver.tex` | `[x]` VERIFIED | γ(t)=(1+t²)/(1+t)²; Δτ_opt=0.58h²/a_max |
| Rhie-Chow correction | `rhie_chow.py` | `07_collocate.tex` | `[x]` VERIFIED (2026-03-21) | 2/(ρ_P^{n+1}+ρ_E^{n+1}) harmonic mean ✓ |
| WENO5 coefficients | `advection.py` | `04_time_integration.tex` | `[x]` VERIFIED (2026-03-21) | β₀,β₁,β₂ Jiang-Shu; d₀=1/10,d₁=3/5,d₂=3/10; ε=1e-6 ✓ |
| TVD-RK3 Shu-Osher coefficients | `tvd_rk3.py` | `09_full_algorithm.tex` | `[x]` VERIFIED (2026-03-21) | Stage coefficients Shu-Osher form ✓ |
| Capillary wave CFL | `cfl.py` | `appendix_numerics_solver.tex` | `[x]` VERIFIED (2026-03-21) | σ/(ρ_min h³) cap. CFL; ν/h² viscous CFL ✓ |
| CSF curvature kernel | `curvature.py` | `03_levelset.tex` / `07_collocate.tex` | `[x]` VERIFIED (2026-03-21) | κ=−(φ_y²φ_xx−2φ_xφ_yφ_xy+φ_x²φ_yy)/|∇φ|³ ✓ |
| Variable-density PPE product rule | `ppe_solver_pseudotime.py` | `08_pressure.tex` | `[x]` VERIFIED (sweep 29) | (1/ρ)∇²p − (∇ρ/ρ²)·∇p ✓ |
| Boundary Eq-II (code vs paper) | `ccd_solver.py:303` | `appendix_ccd_coef.tex` | `[x]` STALE_ENTRY RESOLVED (2026-03-21) | Code uses [2,−5,4,−1]/h² = paper formula; prior discrepancy report was stale |
| Kronecker product 2D CCD assembly | `ppe_solver_pseudotime.py` | `appendix_ccd_impl.tex` (app:ccd_kronecker) | `[x]` VERIFIED (2026-03-21) | kron(D2x,I_Ny)+kron(I_Nx,D2y); C-order k=i·Ny+j ✓ |
| PPE solver strategy (LGMRES/LU) | `ppe_solver_pseudotime.py` | `appendix_ccd_impl.tex` (app:ccd_lu_direct) | `[x]` VERIFIED (2026-03-21) | LGMRES primary (O(n·k) mem), spsolve LU fallback on info≠0 ✓ |

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

- `[x]` Boundary Eq-II discrepancy **RESOLVED**: code uses `[2,−5,4,−1]/h²` which matches paper O(h²) formula; prior discrepancy report was stale (2026-03-21)
- `[x]` Formal MATH_VERIFY for §§1–4 — SAFE (general scan 2026-03-21; no formula errors found)
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
