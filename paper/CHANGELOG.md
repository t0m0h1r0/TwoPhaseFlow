# Changelog

## Paper — CRITIC/EDITOR Passes (2026-03-18)

Seven full CRITIC passes + EDITOR 3rd sweep completed. All D/B/G/L issues resolved.

### EDITOR 3rd sweep (post-7th pass)

| File | Change |
|------|--------|
| `sections/04_ccd.tex` | warnbox L393-398 `{境界スキームの役割と精度}` — split "O(h^5)" claim: Equation-I boundary O(h^5), Equation-II boundary O(h^2), with L² impact note |

### CRITIC 7th pass

| File | Change |
|------|--------|
| `sections/07_pressure.tex` | resultbox — stale BiCGSTAB cross-reference removed |
| `sections/07_pressure.tex` | eq:NS_full — added mybox clarifying Backward Euler derivation vs. CN implementation (eq:crank_nicolson) |
| `sections/07_pressure.tex` | warnbox boundary_cv — retitled "(FVM 実装専用)"; CCD-Poisson boundary redirected to §8.5 |
| `sections/07_pressure.tex` | L.316 — dangling "前処理については下記参照" → reference to §8.5 and tab:ppe_methods |
| `sections/07_pressure.tex` | eq:balanced_force_condition — asymmetric ≈ explained; mybox adds O(ε²) justification |
| `sections/07_pressure.tex` | eq:rc_divergence — p^n (前時刻) explicitly stated in RC face velocity |
| `sections/01_introduction.tex` | L.344 — NS time integration corrected: Forward Euler convection + CN viscous; Chorin O(Δt) bottleneck noted |
| `sections/01_introduction.tex` | tab:chapter_overview Ch4 前提 "3" → "2, 3"; Ch4/Ch5 descriptions updated |
| `sections/01_introduction.tex` | algbox Step 5/6 — scheme names (前進Euler/CN) and ∇_h^RC·u* added |
| `sections/09_full_algorithm.tex` | fig:ns_solvers S1 node — "WENO5/TVD-RK3" → "CCD D^(1)/前進Euler"; caption updated |

### CRITIC passes 3rd–6th

| Pass | File | Change |
|------|------|--------|
| 3rd | `sections/10_verification_metrics.tex` | L93 cross-ref `第\ref{sec:governing}章参照` → `§\ref{sec:balanced_force}参照` |
| 3rd | `sections/03_levelset.tex` | §3.3 warnbox CFL: flux Jacobian `\|1-2ψ\|≤1`; `Δτ_hyp ≤ Δs` |
| 3rd | `sections/00_abstract.tex` | L21 `FVM-PPE` → `CCD-PPE（O(h^6)）` |
| 4th | `sections/03_levelset.tex` | §3.2 stability `Δτ=0.5Δs` → `Δτ=0.25Δs`; N_reinit 14→28 |
| 4th | `sections/01_introduction.tex` | L445 `下図の 7ステップフロー` → `図\ref{fig:algo_flow}の 7ステップフロー` |
| 4th | `sections/09_full_algorithm.tex` | L67 `C_WENO` → `C_CCD` |
| 4th | `sections/03_levelset.tex` | §3.4 false "解析的に行えない" → logit inverse; appendix_proofs.tex created |
| 5th | `sections/08_time_integration.tex` | CLS advection: non-conservative `u·∇ψ` → conservative `∇·(ψu)` |
| 5th | `sections/07_pressure.tex` | tab:accuracy_summary — CSF O(ε²)≈O(h²) row added |
| 5th | `sections/10_verification_metrics.tex` | tab:error_budget NS predictor: WENO5 O(h⁵) → CCD O(h⁶) |
| 5th | `sections/11_conclusion.tex` | `ADI分解による求解` → `逐次Thomas法による求解` |
| 5th | `sections/01_introduction.tex` | `ニュートン法が必要` → logit analytic inverse |
| 5th | `sections/02_governing.tex` | logit fallback note removed; L572 CSF integral proof added; §2.2.3 1D proof → appendix |
| 5th | `sections/03_levelset.tex` | §3.4 warnbox retitled "ロジット逆変換 vs. Sussman 再初期化" |
| 5th | `sections/05_grid.tex` | algbox step 5 — O(h²) formula → CCD method |
| 6th | `sections/09_full_algorithm.tex` | L106+L120-123 ρ/μ interpolation sign corrected (liquid/gas swapped) |
| 6th | `sections/09_full_algorithm.tex` | L119 `(Newton法)` → logit function + Newton fallback |
| 6th | `sections/04_ccd.tex` | L21 4th-order central diff typo `+f_{i+2}` → `+f_{i-2}` |
| 6th | `sections/05_grid.tex` | warnbox dangling "上記の中心差分" fixed; redundant CCD formulas removed |
| 6th | `sections/06_collocate.tex` | L35-115 Helmholtz/Projection scalar φ → Φ (10 instances) |

### CRITIC passes 1st–2nd

| Pass | File | Change |
|------|------|--------|
| 1st | `sections/02_governing.tex` | L418-419 Heaviside φ-axis labels corrected: 液相 (φ<0), 気相 (φ>0) |
| 1st | `sections/11_conclusion.tex` | §7.2 chapter list reordered: Ch4→Ch5→Ch6 |
| 1st | `sections/11_conclusion.tex` | L115-116 spatial bottleneck: WENO5 O(h⁵) → CSF O(ε²)≈O(Δx²) |
| 1st | `sections/04_ccd.tex` | L1 file comment corrected |
| 1st | `sections/05_grid.tex` | L1 file comment corrected |
| 2nd | `sections/09_full_algorithm.tex` | solver box S2 + caption `FVM-PPE` → `CCD-PPE（O(h^6)）` |
| 2nd | `sections/08_time_integration.tex` | §sec:godunov LF wave speed `α=max\|ψ(1-ψ)\|≤1/4` → `α=max\|1-2ψ\|≤1` |
| 2nd | `sections/10_verification_metrics.tex` | tab:error_budget + mybox spatial bottleneck: WENO5 O(h⁵) → CSF O(ε²)≈O(Δx²) |

### tcolorbox refactor (L-2)

Total boxes reduced 49 → 35. §2: 18→13, §3: 20→14, §6: 11→8. All remaining boxes are warnbox, algbox, or defbox for core definitions.

---

## Paper Revision — Pedagogical Expansion (2026-03-16)

### Files Modified

| File | Change |
|------|--------|
| `sections/00_abstract.tex` | Fixed pressure solver description: BiCGSTAB → 仮想時間 CCD 陰解法 |
| `sections/01_introduction.tex` | Swapped table rows 4–5 (Grid/CCD order) + corrected roadmap paragraph order to Grid→CCD |
| `sections/08_time_integration.tex` | Added step-by-step capillary wave time constraint derivation (defbox) |
| `sections/09_full_algorithm.tex` | Corrected C_WENO operator label from 保存形 → 非保存形 with pedagogical note |
| `sections/11_conclusion.tex` | Complete rewrite: 31 lines → ~280 lines with §11.1 design table, accuracy summary, precision mismatch discussion, §11.2 future work, §11.3 learner message |

### Verification

```
xelatex -interaction=nonstopmode main.tex
→ Output written on main.pdf (102 pages, no undefined references)
```

---

## Merged Version (Combined A & B)

### Structural Changes
- **Document Class:** Switched from `article` to `bxjsarticle` (XeLaTeX compliant) as defined in Paper B.
- **Project Structure:** Refactored monads into `paper/sections/` modules.
- **Preamble:** Unified package imports. Preserved `tcolorbox` styles from Paper A (mybox, derivbox, etc.) for detailed equations.
- **Fonts:** Adopted `Times New Roman` and `Hiragino Mincho ProN` (via `xeCJK`) from Paper B.

### Content & Methodology Updates
- **Interface Tracking:** Replaced Standard Level Set (Paper A) with **Conservative Level Set (CLS)** (Paper B). Equations updated to use $\psi$ instead of $\phi$ for advection.
- **Advection Scheme:** Introduced **WENO5** (Paper B) for advection terms, replacing generic references.
- **Rhie-Chow Correction:** Updated the coefficient definition to the harmonically averaged density form found in Paper B.
- **Surface Tension:** Clarified the Balanced-force formulation using CLS variables.

### Content Preservation
- Retained detailed derivations of CCD coefficients (Paper A).
- Retained detailed grid metric transformation rules (Paper A).
- Retained the detailed algorithm flowchart logic (Paper A).
