# CHECKLIST

## §1 — Agent / Prompt Status

| CHK-ID | Status | Type | Location |
|---|---|---|---|
| CHK-001 | CLOSED | audit | prompts/agents/ — 15 agents audited 2026-03-27. 12/15 PASS all 6 STANDARD sections. 3/15 (PromptArchitect, PromptAuditor, PromptCompressor) use `# CONSTRAINTS` instead of `# RULES` — consistent internal variant, not a failure. All have axiom refs and STOP conditions. |
| CHK-002 | CLOSED | docs | docs/ARCHITECTURE.md §1–§2 — populated 2026-03-27 from codebase scan (15 top-level modules, all interface contracts documented) |
| CHK-003 | CLOSED | docs | docs/LATEX_RULES.md §1 — already fully populated (cross-refs, page layout, tcolorbox, texorpdfstring/KL-12, label conventions) |

## §2 — Math / Code Audit Register

| CHK-ID | Status | Type | Location | Verdict | Timestamp |
|---|---|---|---|---|---|
| CHK-020 | CLOSED | test | src/twophase/tests/ — 95/95 tests pass, 0 warnings | PASS | 2026-03-27 |
| CHK-021 | CLOSED | test | src/twophase/tests/test_simulation.py — 3 integration tests: builder constructs, step_forward no NaN/Inf, Laplace pressure sign positive | PASS | 2026-03-27 |
| CHK-022 | CLOSED | test | Full suite after Priority 2: 98/98 pass, 0 warnings | PASS | 2026-03-27 |

## §3 — Paper / Compile Status

| CHK-ID | Status | Type | Location |
|---|---|---|---|
| CHK-010 | CLOSED | compile | paper/ — XeLaTeX 2-pass clean: 139 pages, 0 errors, 0 overfull/underfull, 0 undefined refs, rerunfilecheck stable (2026-03-27) |
| CHK-011 | CLOSED | review | PaperReviewer full audit (main + appendix) 2026-03-27: 2 fatal, 12 high-priority issues found and classified |
| CHK-012 | CLOSED | fix | PaperCorrector — 6 high-priority fixes applied 2026-03-27: (1) Φ→q rename in 07_collocate.tex; (2) ALE 必須→強く推奨 in appendix_numerics_schemes_s1.tex; (3) §\ref→付録~\ref in appendix_ccd_impl_s3.tex; (4) Eq-II O(h⁴) 今後の課題→実装済み in appendix_ccd_impl_s3.tex; (5) γ(t)/LU wording clarified in appendix_ccd_impl_s3.tex; (6) ghost cell reflection scope note in appendix_ccd_impl_s1.tex. Compile: 139 pages, 0 errors. |
| CHK-013 | CLOSED | fix | PaperWriter 5 items written 2026-03-27: (a) sec:ppe_gauge_neumann in 08d — Neumann solvability + center-node gauge; (b) result:dccd_stability in 05_advection — TVD-RK3 CFL bound σ_max≈0.91; (c) box:cn_tridiagonal in 05b — tridiagonal coefficients for x/y sweeps; (d) box:grid_modes in 06_grid — Mode 1/Mode 2 with bootstrap explanation; (e) sec:lambda_max_derive in appendix_numerics_solver_s2 — Eq-II Fourier analysis giving 4.8/h², empirical 3.43/h². Compile: 142 pages, 0 errors. |
| CHK-014 | CLOSED | fix | PaperCorrector 3 fixes applied 2026-03-27: (1) 06_grid.tex resultbox line 65 — added title={座標変換公式（厳密形）} + \label{box:transform_formula}; (2) 06_grid.tex algbox title + step 3 text — "台形則" → "前進矩形則（左端点則）" to match actual formula x̃_{i+1}=x̃_i+Δξ/ω_i; (3) 05_advection.tex — added k=ξ/h definition before eq:ccd_adv_instability. Issue (1) duplicate labels: REVIEWER_ERROR — appendix_numerics_solver.tex / appendix_numerics_schemes.tex not \input'd in main.tex. Compile: 142 pages, 0 errors, 0 undefined refs. |

## Format reference

`CHK-ID | status: OPEN / IN_PROGRESS / CLOSED / UNKNOWN | type | location`
