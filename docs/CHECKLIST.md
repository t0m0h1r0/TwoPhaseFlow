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
| CHK-015 | CLOSED | fix | PaperCorrector 6 fixes applied 2026-03-28 (PaperReviewer 2nd-pass issues): [F-1] 05_advection.tex:133 + 05b_time_integration.tex:21 — L(ψ)=F̃ → L(ψ)=−F̃ (fatal sign error; PDE consistency); [F-2] 05_advection.tex:153 + 07_collocate.tex:254,262 — "数値実験で確認している/確認済み" → "今後の課題" language (false confirmed claims); [F-3] 00_abstract.tex:25 — added \footnote for O(Δt) accuracy degradation at interface; [F-4] 05_advection.tex — added bridge sentence: filter alone |g|²>1 → unstable; TVD-RK3 CFL σ_max≈0.91 provides actual stabilization; [M-1] 04b_ccd_bc.tex:208 + 04d_dissipative_ccd.tex:170 — defbox: labels renamed to box: (LATEX_RULES §1 compliance); [G-1] 06_grid.tex:271 — added δ≳0.5h quantitative criterion for Mode 1 resolution loss. Compile: 142 pages, 0 errors, 0 warnings (2026-03-28). |

| CHK-016 | CLOSED | fix | PaperCorrector [M-2] 2026-03-28: 5 monolithic appendix files (appendix_interface/ccd_coef/ccd_impl/numerics_schemes/numerics_solver .tex) replaced their duplicated content with \input{} delegation to the corresponding _s*.tex split files. main.tex updated: 21 individual split \input lines → 5 monolithic \input lines (no content change; duplication eliminated). |
| CHK-017 | CLOSED | compile | PaperCompiler 2026-03-28: XeLaTeX 2-pass clean after CHK-015+CHK-016 fixes. 142 pages, 0 errors, 0 warnings, 0 overfull/underfull, 0 undefined refs. texorpdfstring pre-scan: 0 hits. |
| CHK-018 | CLOSED | fix | PaperCorrector [M-1] 2026-03-28: 02b_csf.tex:179,183 — \label{proof:csf_young_laplace} + \ref{proof:...} renamed to \label{sec:csf_young_laplace} + §\ref{sec:...} (LATEX_RULES §1: proof: not an allowed prefix). |
| CHK-019 | CLOSED | fix | PaperCorrector [M-3] 2026-03-28: 04b_ccd_bc.tex:208 — removed orphaned \label{box:ccd_numeric_blocks} placed outside any tcolorbox (no matching \ref{} in document); also fixed "上記の記号形" → 式~\eqref{eq:ccd_block} の記号形 (M-4 cascade). |
| CHK-020 | CLOSED | fix | PaperCorrector [M-4] 2026-03-28: 7 relative positional text violations fixed — (1) 04_ccd.tex:49 "上式" → explicit formula; (2) appendix_numerics_schemes_s3.tex:42 "上式" → "この"; (3) 08d_ppe_pseudotime.tex:282 "上記の条件" → "いずれの設定も"; (4) 09_full_algorithm.tex:94 "上記オペレータ一覧参照" dropped; (5) 09_full_algorithm.tex:206 "上記 L_visc" → §\ref{sec:time_int}; (6) 10b_benchmarks.tex:206 "上記パラメータ" → "推奨設定値に基づく"; (7) 06_grid.tex:176,215 "上記ステップ1"/"上記アルゴリズム" → explicit refs. Compile: 142 pages, 0 errors, 0 warnings (2026-03-28). |

## Format reference

`CHK-ID | status: OPEN / IN_PROGRESS / CLOSED / UNKNOWN | type | location`
