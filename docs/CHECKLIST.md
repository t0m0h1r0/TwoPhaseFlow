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
| Boundary Eq-II (code coupled) | `ccd_solver.py:300` | — | `[!]` DISCREPANCY | Code uses `[−325/18,…]/h²`; paper shows O(h²) formula. Tests pass. Needs doc. |
| PPE pseudo-time convergence | `ppe_solver_pseudotime.py` | `08_pressure.tex` / `appendix_numerics_solver.tex` | `[x]` VERIFIED | γ(t)=(1+t²)/(1+t)²; Δτ_opt=0.58h²/a_max |
| Rhie-Chow correction | `rhie_chow.py` | `07_collocate.tex` | `[ ]` TODO | |
| WENO5 coefficients | `advection.py` | `04_time_integration.tex` | `[ ]` TODO | β₀,β₁,β₂ smoothness indicators |
| TVD-RK3 Shu-Osher coefficients | `tvd_rk3.py` | `09_full_algorithm.tex` | `[ ]` TODO | Stage coefficients |
| Capillary wave CFL | `cfl.py` | `appendix_numerics_solver.tex` | `[ ]` TODO | |
| CSF curvature kernel | `curvature.py` | `03_levelset.tex` / `07_collocate.tex` | `[ ]` TODO | |
| Variable-density PPE product rule | `ppe_solver_pseudotime.py` | `08_pressure.tex` | `[x]` VERIFIED (sweep 29) | (1/ρ)∇²p − (∇ρ/ρ²)·∇p ✓ |

---

## 3. LaTeX Build

- `[x]` `pdflatex` clean — 0 errors, 0 undefined references (last confirmed: sweep 29, 2026-03-21)
- `[x]` Page count stable: **116 pages**
- `[ ]` Next full re-build after any structural change (add to agenda when .tex is modified)

---

## 4. Code Test Suite

- `[x]` `pytest src/twophase/tests/` — **28 tests passing** (as of 2026-03-21)
- `[ ]` Benchmark at N=128 (higher-resolution confirmation)
- `[ ]` GPU backend (CuPy) compatibility check
- `[ ]` 3D cases
- `[ ]` VTK output writer (`io/`)

---

## 5. Open Action Items

### Paper / Documentation

- `[!]` Boundary Eq-II **DISCREPANCY**: code uses coupled high-order scheme `[−325/18, 39/2, −3/2, 1/18]/h²`; paper describes O(h²) formula `(2f₀−5f₁+4f₂−f₃)/h²`. Both are valid; needs documentation of which is canonical and why the code differs. (See `13_MATH_VERIFY.md` Verification Register.)
- `[ ]` Formal MATH_VERIFY for §§1–4 (not yet done in MATH_VERIFY protocol)
- `[ ]` Formal MATH_VERIFY for Rhie-Chow, WENO5, TVD-RK3, CSF curvature (see §2 table above)
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
