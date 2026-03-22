# LESSONS LEARNED

Accumulated lessons from past audit and review sessions.
**Append new entries here — do not add state to numbered workflow docs.**

---

## A. Mathematical Audit Error Patterns (KL-xx)

Referenced by `docs/13_MATH_VERIFY.md`. Check every audit against these patterns first.

---

### KL-01: Block Matrix (2,1) Sign Flip After RHS Transposition

**Found:** 2026-03-20
**Location:** `paper/sections/05b_ccd_bc_matrix.tex` defbox (l.147, l.153, l.215, l.221)
**Error:** The paper wrote A_L(2,1) = −b₂/h = +9/(8h) (positive). Correct value is +b₂/h = −9/(8h) (negative).

**Root cause:** The RHS term `(b₂/h)(f'_{i+1} − f'_{i-1})` gives `f'_{i-1}` a coefficient of **−b₂/h** (not +b₂/h) because of the subtraction. Transposing −b₂/h to LHS gives +b₂/h. The paper incorrectly treated the coefficient as positive before transposing.

**Generalised rule:** In any scheme of the form `= C·(X_{i+1} − X_{i-1})`, the `X_{i-1}` coefficient on the RHS is **−C**, not +C. LHS after transposition: **+C**.

**Steps for every block-matrix audit:**
- Verify A_L(2,1) = +b₂/h; with b₂ = −9/8 this is negative (−9/(8h))
- Verify A_R(2,1) = −b₂/h; with b₂ = −9/8 this is positive (+9/(8h))
- Confirm code `lower[k][1,0]` = `_B2/h` < 0
- Confirm code `upper[k][1,0]` = `-_B2/h` > 0

---

### KL-02: Wrong Block Size in Documentation

**Found:** 2026-03-20
**Location:** `docs/ARCHITECTURE.md`
**Error:** Written as "3×3 blocks"; correct is **2×2** (unknowns per node = [f′, f″] = 2 components).
**Rule:** Block size = number of unknowns per grid node. For CCD: f′ and f″ → 2×2.

---

### KL-03: Pseudocode Comment Mismatch

**Found:** 2026-03-21
**Location:** `paper/sections/06_grid.tex` l.227
**Error:** Comment `# 台形則で累積積分` but the loop `x_tilde[i+1] = x_tilde[i] + dxi/omega[i]` is a forward (left) Riemann sum, not the trapezoidal rule.

**Root cause:** The trapezoidal rule would average `omega[i]` and `omega[i+1]`. The code uses only `omega[i]` (left endpoint). This is a documentation error; the algorithm is valid but the comment misnames it.

**Generalised rule:** When a pseudocode comment names a specific numerical method ("台形則", "Euler", "RK4"), verify that the code body matches exactly. Trapezoidal requires `(f[i] + f[i+1])/2`; Euler / Riemann uses `f[i]` alone. This category of error is invisible to tests.

---

### KL-04: Operator Leibniz Rule — D(κf) ≠ κ·D(f) for Spatially Varying κ

**Found:** 2026-03-21
**Location:** `paper/sections/07_collocate.tex` l.311–313
**Error:** The paper wrote `D_CCD p − (κ/We)D_CCD ψ = D_CCD(p − κψ/We)`, factoring κ out of D_CCD. This is only valid for spatially constant κ. In general: `D_CCD(κψ/We) = (κ/We)D_CCD ψ + (ψ/We)D_CCD κ`.

**Root cause:** Leibniz (product) rule for differential operators: `D(fg) = fDg + gDf`. κ (curvature) varies along the interface, so it cannot be factored out.

**Correction:** The conclusion O(h⁶) is still correct via the direct argument: in equilibrium each term individually approximates ∇(·) with O(h⁶) accuracy, so `D_CCD p − (κ/We)D_CCD ψ = ∇p − (κ/We)∇ψ + O(h⁶) = O(h⁶)`.

**Generalised rule:** Whenever a paper writes `D(κf) = κD(f)` for a differential operator D and a spatially varying field κ, check whether κ is truly constant in the context. In two-phase CFD, κ (curvature), ρ, μ are all spatially varying. The factoring is only valid on the interface where κ is evaluated at a fixed point.

---

### KL-05: Nyquist Modified Wavenumber ≠ Finite-Grid Spectral Radius

**Found:** 2026-03-21
**Location:** `paper/sections/08b_ccd_poisson.tex` l.91
**Error:** The paper wrote `ρ(L_CCD^x) ≈ 4a₂/[(1+2|β₂|)h²] ≈ 3.43/h²`. For a₂=3, β₂=−1/8: `4·3/[(1+0.25)h²] = 9.6/h²`, not 3.43/h².

**Root cause:** Two distinct quantities were conflated:
1. **Infinite-periodic modified wavenumber at k=π/h:** From Fourier analysis of the scheme on an infinite periodic grid. This gives 9.6/h². It is an UPPER BOUND, rarely achieved on finite grids.
2. **Finite-grid spectral radius (Neumann BCs):** The actual maximum eigenvalue of the CCD Laplacian matrix on a finite domain. Numerically ≈ 3.43/h², consistent with the empirically validated Δτ_opt = 0.58h²/a_max → λ_max = 2/Δτ_opt ≈ 3.45/h².

**Generalised rule:** For compact implicit difference schemes (Padé, CCD), never equate the modified wavenumber at k=π/h with the spectral radius of the finite-grid matrix. The finite-grid eigenvalues are bounded by the continuous spectrum (≈ π²/h² for the 1D Laplacian), and for moderate N with Neumann BCs the maximum eigenvalue is typically close to 4/h² (similar to standard FD), not the Nyquist formula.

---

### KL-06: Pre-Asymptotic vs Asymptotic Convergence Rate

**Found:** 2026-03-21
**Location:** `paper/sections/10_verification.tex` l.92
**Error:** Table shows O(h⁴) convergence for spurious currents at N=32–128; asymptotic theoretical rate stated elsewhere is O(h²). Without clarification, readers may conclude O(h⁴) is the asymptotic rate.

**Root cause:** At moderate N (32–128), CSF model error O(ε²)≈O(h²) has not yet overtaken the discrete spatial discretization error. The O(h⁴) behavior is pre-asymptotic: as N increases further, the CSF model floor dominates and the apparent order drops to O(h²).

**Generalised rule:** Any convergence table that covers only 2–3 grid doublings risks reporting pre-asymptotic rates. Always accompany such tables with: (a) the theoretical asymptotic prediction, (b) an explicit note that the table range is pre-asymptotic if applicable, and (c) a cross-reference to the section that establishes the asymptotic theory.

---

### KL-07: "Conservative" CFL Rounding Direction Error

**Found:** 2026-03-21
**Location:** `paper/sections/appendix_numerics_solver.tex` l.181
**Error:** Text said "保守的に 1/√(2π) に丸めると" (round conservatively to 1/√(2π)). Derived coefficient is 2/(3√π)≈0.376; 1/√(2π)≈0.399 > 0.376, so the "rounded" value allows a **6% larger** Δt. This is less conservative (more permissive), not more.

**Root cause:** Direction confusion: "conservative" in a CFL context means SMALLER Δt (tighter bound). Rounding UP the coefficient gives a larger Δt — which is LESS conservative. The author likely intended to simplify the expression and used the nearest "clean" fraction without checking the direction.

**Generalised rule:** For CFL constraints `Δt ≤ C·f(h)`, conservative means smaller C. If you round the derived coefficient to a nearby "clean" value, verify: `C_rounded ≤ C_exact` (tighter) for conservative, `C_rounded ≥ C_exact` (looser) for aggressive. Always state the direction explicitly and verify numerically.

---

### KL-08: Kronecker Product Index Convention — C-Order vs. Fortran-Order

**Found:** 2026-03-21
**Location:** `paper/sections/appendix_ccd_impl.tex` `app:ccd_kronecker` (added 2026-03-21)
**Risk:** The Kronecker product formulas `D2x ⊗ I_Ny` and `I_Nx ⊗ D2y` are correct **only** when the 2D array is flattened in C-order (row-major: k = i·Ny + j). If Fortran-order (column-major: k = j·Nx + i) is used instead, the roles of the two factors swap.

**NumPy default:** `array.ravel()` uses C-order by default. `scipy.sparse.kron(A, B)` assembles the block structure consistent with C-order when A acts on the slow (row) index and B on the fast (column) index. This is exactly `D2x ⊗ I_Ny` for x (slow) and `I_Nx ⊗ D2y` for y (fast).

**Steps for any Kronecker product 2D operator:**
- Confirm data layout: `p.ravel()` is C-order → flat index k = i·Ny + j
- `kron(D_axis0, I_axis1)` for axis-0 (x) derivative
- `kron(I_axis0, D_axis1)` for axis-1 (y) derivative
- Verify against code: `sp.kron(D2x, sp.eye(Ny))` ← D2x ⊗ I_Ny
- Cross-check: feed a known polynomial and compare `kron` matrix-vector product against `ccd.differentiate` pointwise result. Max difference must be exactly 0.

**Generalised rule:** For a 2D array stored in C-order with shape (Nx, Ny), the partial derivative operator along axis ℓ is:
```
L_full = kron(D_ℓ, I_other)   if ℓ = 0 (slow index, x)
       = kron(I_other, D_ℓ)   if ℓ = 1 (fast index, y)
```
For 3D arrays (Nx, Ny, Nz) in C-order: axis-0 → `D⊗I_y⊗I_z`, axis-1 → `I_x⊗D⊗I_z`, axis-2 → `I_x⊗I_y⊗D`.

---

### KL-09: Solver Strategy — Iterative Primary, LU Fallback (PPE)

**Found:** 2026-03-21 (initial discrepancy); **Updated:** 2026-03-21 (design clarification)
**Location:** `appendix_ccd_impl.tex` app:ccd_lu_direct; `ppe_solver_pseudotime.py:solve()`

**Design intent (confirmed 2026-03-21):**
- PRIMARY: LGMRES iterative solver — O(n·k) memory, warm start from p_init.
- FALLBACK: sparse direct LU (`spsolve`) — invoked automatically when LGMRES does not
  converge within `pseudo_maxiter` steps. Ensures no blocking of downstream development.

**Root cause of needing fallback:** CCD one-sided boundary schemes (Eq-II-bc) produce a
highly asymmetric matrix (max asymmetry ≈ 900 for N=16). Standard GMRES diverges on some
grids; LGMRES is more robust but not guaranteed to converge.

**Solver policy scope:**
- PPE global sparse system: iterative primary, LU fallback (memory efficiency).
- CCD block tridiagonal (Thomas sweeps), Helmholtz 1D: direct LU (banded — LU fill-in is O(N)).

**Paper ref:** `appendix_ccd_impl.tex` §app:ccd_lu_direct (updated to match this design).

**Generalised rule:** For large unstructured sparse systems, always design iterative-primary/
LU-fallback so that convergence issues never block development. For banded systems where
direct LU fill-in is provably O(N), prefer direct LU outright.

---

### KL-10: Collocated-Grid Corrector — RC vs CCD Divergence-Free

**Found:** 2026-03-22
**Location:** `09_full_algorithm.tex:246`; `velocity_corrector.py`; `ppe_solver_pseudotime.py`

**Error:** Paper claimed `D_x^(1)u^{n+1}+D_y^(1)v^{n+1}=0` (CCD divergence-free exactly).

**Derivation:** With CCD corrector `u^{n+1} = u* − (Δt/ρ) D^(1)_CCD δp` and
PPE `L_CCD^ρ δp = (1/Δt) ∇^RC · u*`, applying CCD divergence gives:
```
D_CCD · u^{n+1} = D_CCD · u* − Δt L_CCD^ρ δp = D_CCD · u* − ∇^RC · u* = O(h²)
```
The Rhie-Chow detection term `∇^RC·u* − D_CCD·u* = O(h²)` remains as a residual.
The velocity IS divergence-free in the `∇^RC` (Rhie-Chow) sense.

**Fix:** Paper now states `∇_h^RC · u^{n+1} = 0` with O(h²) note for CCD sense.

**Generalised rule:** When PPE RHS uses RC divergence for checkerboard stability, the
corrector produces `∇^RC · u^{n+1} = 0`, not `D_CCD · u^{n+1} = 0`. Never claim
exact CCD-divergence-free after a collocated-grid projection step.

---

### KL-11: Pin Node Exclusion Must Track Pin Location

**Found:** 2026-03-22
**Location:** `ppe_solver_pseudotime.py:compute_residual()` line 230

**Error:** `solve()` moved pin from corner (0,0) to center (N//2,N//2) in 2026-03-22 commit.
`compute_residual()` still excluded `ravel()[0]` (corner), not the actual pin node.

**Fix:** Replaced hardcoded `ravel()[0] = 0.0` with dynamic `ravel()[pin_dof] = 0.0`
where `pin_dof = ravel_multi_index(tuple(n//2 for n in grid.N), grid.shape)`.

**Generalised rule:** When pin location is changed, grep for ALL hardcoded references
to the old pin index (especially diagnostic residual methods). Use the same
`pin_idx = tuple(n // 2 for n in grid.N)` expression everywhere.

---

## B. Reviewer / AI Hallucination Patterns

Referenced by `docs/11_PAPER_EDITOR.md`. Watch for these in every review cycle.

These patterns were observed in the 2026-03-21 editorial session (15+ reviewer claims examined; the vast majority were REVIEWER_ERROR).

1. **Formula Swap:** Reviewer's "fix suggestion" column describes the correct formula that is already in the paper. The reviewer claims the paper has the wrong formula, but in fact the paper already has the "fix." Reading the actual file immediately exposes this.

2. **Misread Table Row:** Reviewer attributes a numerical value to the wrong row of a results table. Always read the table directly; identify which benchmark the value belongs to.

3. **Cascading False Premise:** Reviewer opens with "given the errors in Chapter X..." but those "errors" are themselves REVIEWER_ERROR. All subsequent claims in the same review then inherit the false premise. Identify the root premise and verify it first.

4. **Chapter/Section Number Mismatch:** Reviewer uses a different numbering scheme than the paper. A claim about "Chapter 5" may map to the paper's §7 or §8. Verify by content matching, not numbering.

5. **Scope vs. Error Confusion:** Reviewer flags an approximation, boundary condition, or limiting assumption as an "error." Check §11 (Conclusion/Future Work) and any warnbox near the flagged section — the limitation may already be explicitly acknowledged.

6. **Correct Formula, Wrong Attribution:** Reviewer says "the paper uses formula A (wrong), should use formula B (correct)" but the paper actually uses formula B. This is the most common hallucination.

7. **Leibniz Rule Shortcut:** Reviewer (or prior editor) writes `D(κf) = κD(f)` and factors a spatially-varying quantity κ out of a differential operator D. This is only valid for constant κ. See KL-04.

8. **Nyquist Formula ≠ Finite-Grid Spectral Radius:** A reviewer states a compact scheme's spectral radius using the infinite-periodic modified wavenumber at k=π/h. See KL-05.

9. **Pre-Asymptotic vs Asymptotic Rate:** Reviewer mistakes a pre-asymptotic measurement for the theoretical asymptote. See KL-06.

10. **Conservative Rounding Direction:** A CFL coefficient claimed to be "conservative" is actually larger than the derived value — making it less conservative. See KL-07.
