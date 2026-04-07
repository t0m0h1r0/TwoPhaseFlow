---
ref_id: WIKI-P-004
title: "Paper Review §1–§11: Findings and Action Items (2026-04-08)"
domain: A
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/01_introduction.tex
  - path: paper/sections/02_governing.tex
  - path: paper/sections/02b_surface_tension.tex
  - path: paper/sections/02c_nondim_curvature.tex
  - path: paper/sections/03_levelset.tex
  - path: paper/sections/03b_levelset_mapping.tex
  - path: paper/sections/04_ccd.tex
  - path: paper/sections/04b_ccd_bc.tex
  - path: paper/sections/04d_dissipative_ccd.tex
  - path: paper/sections/05_grid.tex
  - path: paper/sections/05b_ccd_extensions.tex
  - path: paper/sections/06_time_integration.tex
  - path: paper/sections/07_advection.tex
  - path: paper/sections/07b_reinitialization.tex
  - path: paper/sections/08_collocate.tex
  - path: paper/sections/08b_pressure.tex
  - path: paper/sections/08c_pressure_filter.tex
  - path: paper/sections/09_ccd_poisson.tex
  - path: paper/sections/09b_defect_correction.tex
  - path: paper/sections/09c_ppe_bc.tex
  - path: paper/sections/09d_pressure_summary.tex
  - path: paper/sections/10_full_algorithm.tex
  - path: paper/sections/11_chapter.tex
  - path: paper/sections/11_spatial.tex
  - path: paper/sections/11_interface.tex
  - path: paper/sections/11_solver.tex
  - path: paper/sections/11_summary.tex
consumers:
  - domain: A
    usage: "PaperWriter/PaperCorrector action list"
depends_on:
  - "[[WIKI-P-001]]"
  - "[[WIKI-P-002]]"
compiled_by: PaperReviewer
---

# Paper Review §1–§11: Findings (2026-04-08)

## Verdict
- **Fatal [F]**: 0
- **Major [M]**: 7
- **Minor [m]**: 14
- **Style [S]**: 3
- **Mathematical rigor**: HIGH — CCD coefficients, curvature invariance theorem, sign conventions independently verified
- **Pedagogical quality**: HIGH — stepwise derivations, algorithm boxes, failure mode analysis

## Major Issues (M)

### M-1: Discrete divergence estimate unclear (§3)
- **File**: 03_levelset.tex:289
- **Issue**: `[∇·u]_h = O(Δt·h²/Δt) = O(h²)` — intermediate expression dimensionally suspicious
- **Action**: Clarify derivation or replace with standard IPC splitting error analysis

### M-2: Warnbox contradicts Step 5 implementation (§4 ext)
- **File**: 05b_ccd_extensions.tex:28
- **Issue**: Claims Step 5 uses O(h²) central difference; actual Step 5 (05_grid.tex:114) uses CCD O(h⁶)
- **Action**: Rewrite to hypothetical form: "If J_x were evaluated with O(h²)..."

### M-3: File header mismatch (§8)
- **File**: 08_collocate.tex:0 says `07_collocate.tex`
- **Action**: Update file header comment

### M-4: Gradient filter divergence-free impact unquantified (§8c)
- **File**: 08c_pressure_filter.tex
- **Issue**: Claims filtering ∇p preserves divergence-free; actually introduces O(Δt·h²) consistency error
- **Action**: Add error estimate or acknowledge trade-off

### M-5: DC relaxation convergence bound (§9b)
- **File**: 09b_defect_correction.tex:64
- **Issue**: ω < 0.833 bound references appendix only; needs inline verification summary
- **Action**: Add 1-line derivation or spectral radius citation

### M-6: §1 chapter table outdated (§1 vs §11)
- **File**: 01_introduction.tex:490-494
- **Issue**: Table says §10=Component Verification, §11=Multiphase Benchmark; actual §11 is component verification
- **Action**: Update table to match current section structure

### M-7: Verification summary lacks explicit PASS/FAIL (§11)
- **File**: 11_summary.tex
- **Issue**: Table 11.16 has no "Status" column; 2 known failures implicit only
- **Action**: Add PASS/FAIL column; highlight failures prominently

## Minor Issues (m)

| ID | File | Issue |
|----|------|-------|
| m-1 | 02b_surface_tension.tex:45 | TODO: "rename to HFE in final draft" |
| m-2 | 02b_surface_tension.tex:9 | Orphaned label `eq:Heps_def_preview` — verify usage |
| m-3 | 01_introduction.tex:493 | Table §10/§11 mismatch (→ M-6) |
| m-4 | 05_grid.tex:4-12 | Opening paragraph duplicated |
| m-5 | 06_time_integration.tex:0, 05b_ccd_extensions.tex:0 | File header vs filename mismatch |
| m-6 | 08_collocate.tex:0 | File header `07_collocate` vs filename `08_collocate` |
| m-7 | 07b_reinitialization.tex:110 | n_reinit=4 default lacks convergence reference |
| m-8 | Cross-file | ε_d values (0.05, 0.05, 1/4) scattered; §10 has summary table |
| m-9 | 07b_reinitialization.tex:49 | δ=10⁻⁸ selection rationale missing |
| m-10 | 09c_ppe_bc.tex | Orphaned ref to `sec:ppe_gauge_neumann` |
| m-11 | 09d_pressure_summary.tex | "O(h²)/O(h⁶)" dual notation confusing |
| m-12 | 10_full_algorithm.tex | ε_d=1/4 exceeds accuracy design ε_d,max=0.05 (acknowledged in box) |
| m-13 | 11_interface.tex | Young-Laplace convergence from 1 grid pair only |
| m-14 | 11_chapter–summary | No unified numbered test inventory table |

## Independently Verified Correct

1. **CCD coefficients**: α₁=7/16, a₁=15/16, b₁=1/16; β₂=-1/8, a₂=3, b₂=-9/8 — all 6 conditions ✓
2. **Boundary Eq-II**: (2f₀-5f₁+4f₂-f₃)/h² = f₀'' + O(h²) with coefficient -11/12 ✓
3. **Sign convention**: κ=-∇·n̂, φ<0=liquid, [p]=σκ=-σ/R<0 for droplet ✓
4. **Curvature invariance theorem**: Proof via chain rule g'>0 ⟹ n̂_ψ = n̂_φ ✓
5. **DCCD transfer function**: H(ξ)=1-4ε_d sin²(ξ/2), stability ε_d≤1/4 ✓
6. **Switch function**: S(ψ)=(2ψ-1)²=tanh²(φ/2ε) ✓
7. **Product-rule PPE**: ∇·(1/ρ ∇p) = (1/ρ)∇²p - (∇ρ/ρ²)·∇p ✓
8. **§11 convergence orders**: All consistent with §4 (CCD) and §9 (PPE) predictions ✓
9. **Physical property interpolation**: ρ⁻¹ harmonic mean = 2/(ρ_L+ρ_R), μ arithmetic mean ✓
10. **Δτ stability**: min(0.5h²/(2N_dim·ε), 0.5h) dimensionally consistent in non-dim system ✓
