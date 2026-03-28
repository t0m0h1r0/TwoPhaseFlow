# 02_ACTIVE_LEDGER — Phase, Branch, CHK Register, Assumptions & Lessons
# LIVE document — append-only for CHK/ASM/KL entries; phase/branch updated each session.
# Supersedes: ACTIVE_STATE.md, CHECKLIST.md, ASSUMPTION_LEDGER.md, LESSONS.md
# Last updated: 2026-03-28

────────────────────────────────────────────────────────
# § ACTIVE STATE

| Key | Value |
|---|---|
| phase | BOOTSTRAP_COMPLETE |
| branch | dev2 |
| last_decision | CHK-038 CLOSED 2026-03-28: CodeReviewer refactor — 8 LOW_RISK changes applied (R-01–R-07, R-02); R-08 SKIPPED (ReinitializerWENO5 DO NOT DELETE §C2); R-10–R-14 HIGH_RISK deferred. 98/98 tests PASS. |
| next_action | None — CHK-039/040 closed. Project in clean state. |

### Notes
- External memory structure initialized from scratch — prior state was implicit (no docs/).
- All agent prompts aligned to STANDARD PROMPT TEMPLATE (section headers standardized).
- Meta-agents (PromptArchitect, PromptAuditor, PromptCompressor) use `# CONSTRAINTS` instead of
  `# RULES` — consistent internal variant, not a defect.
- `docs/01_PROJECT_MAP.md §1` corrected: old `solver/` subtree replaced with actual layout.
- 2026-03-28: Domain-Oriented Architecture (Meta-as-Master) applied. docs/ files consolidated:
  ACTIVE_STATE+CHECKLIST+ASSUMPTION_LEDGER+LESSONS → 02_ACTIVE_LEDGER.md;
  ARCHITECTURE → 01_PROJECT_MAP.md; CODING_POLICY+LATEX_RULES absorbed into meta-tasks.md.
  prompts/agents/GLOBAL_RULES.md superseded by docs/00_GLOBAL_RULES.md.

────────────────────────────────────────────────────────
# § CHECKLIST

## §1 — Agent / Prompt Status

| CHK-ID | Status | Type | Location |
|---|---|---|---|
| CHK-001 | CLOSED | audit | prompts/agents/ — 16 agents audited 2026-03-28 after PromptCompressor pass. All PASS (PromptCompressor step numbering defect fixed). |
| CHK-002 | CLOSED | docs | docs/01_PROJECT_MAP.md §1–§2 — populated from codebase scan (15 top-level modules, all interface contracts documented) |
| CHK-003 | CLOSED | docs | docs/00_GLOBAL_RULES.md §P1 — authoritative LaTeX standard (replaces LATEX_RULES.md) |

## §2 — Math / Code Audit Register

| CHK-ID | Status | Type | Location | Verdict | Timestamp |
|---|---|---|---|---|---|
| CHK-020 | CLOSED | test | src/twophase/tests/ — 95/95 tests pass, 0 warnings | PASS | 2026-03-27 |
| CHK-021 | CLOSED | test | src/twophase/tests/test_simulation.py — 3 integration tests: builder constructs, step_forward no NaN/Inf, Laplace pressure sign positive | PASS | 2026-03-27 |
| CHK-022 | CLOSED | test | Full suite after Priority 2: 98/98 pass, 0 warnings | PASS | 2026-03-27 |

## §3 — Paper / Compile Status

| CHK-ID | Status | Type | Location |
|---|---|---|---|
| CHK-010 | CLOSED | compile | paper/ — XeLaTeX 2-pass clean: 139 pages, 0 errors, 0 overfull/underfull, 0 undefined refs (2026-03-27) |
| CHK-011 | CLOSED | review | PaperReviewer full audit (main + appendix) 2026-03-27: 2 fatal, 12 high-priority issues found and classified |
| CHK-012 | CLOSED | fix | PaperCorrector — 6 high-priority fixes applied 2026-03-27: (1) Φ→q rename in 07_collocate.tex; (2) ALE 必須→強く推奨; (3) §\ref→付録~\ref; (4) Eq-II O(h⁴) 今後の課題→実装済み; (5) γ(t)/LU wording; (6) ghost cell reflection scope note. Compile: 139pp, 0 errors. |
| CHK-013 | CLOSED | fix | PaperWriter 5 items written 2026-03-27: (a) sec:ppe_gauge_neumann in 08d; (b) result:dccd_stability in 05_advection; (c) box:cn_tridiagonal in 05b; (d) box:grid_modes in 06_grid; (e) sec:lambda_max_derive in appendix_numerics_solver_s2. Compile: 142pp, 0 errors. |
| CHK-014 | CLOSED | fix | PaperCorrector 3 fixes 2026-03-27: (1) 06_grid.tex resultbox title+label; (2) 06_grid.tex algbox "台形則"→"前進矩形則"; (3) 05_advection.tex k=ξ/h definition added. Compile: 142pp, 0 errors, 0 undefined refs. |
| CHK-015 | CLOSED | fix | PaperCorrector 6 fixes 2026-03-28: [F-1] L(ψ)=F̃→L(ψ)=−F̃ (fatal sign); [F-2] "数値実験で確認"→"今後の課題"; [F-3] \footnote for O(Δt) degradation; [F-4] filter stability bridge sentence; [M-1] defbox→box: labels; [G-1] δ≳0.5h criterion. Compile: 142pp, 0 errors, 0 warnings. |
| CHK-016 | CLOSED | fix | PaperCorrector [M-2] 2026-03-28: 5 monolithic appendix files replaced duplicated content with \input{} delegation. main.tex: 21 split \input lines→5 monolithic (no content change). |
| CHK-017 | CLOSED | compile | PaperCompiler 2026-03-28: XeLaTeX 2-pass clean after CHK-015+CHK-016. 142pp, 0 errors, 0 warnings, texorpdfstring pre-scan: 0 hits. |
| CHK-018 | CLOSED | fix | PaperCorrector [M-1] 2026-03-28: 02b_csf.tex:179,183 — \label{proof:csf_young_laplace}→\label{sec:csf_young_laplace} (LATEX_RULES §1: proof: not allowed). |
| CHK-019 | CLOSED | fix | PaperCorrector [M-3] 2026-03-28: 04b_ccd_bc.tex:208 — orphaned \label removed; "上記の記号形"→式~\eqref{eq:ccd_block}の記号形 (M-4 cascade). |
| CHK-023 | CLOSED | fix | PaperCorrector 3 fixes 2026-03-28 (§10b audit): [M-1] O(h^p)(p≥4)→O(h^2)(CSF律速); [m-2] "Re=100相当" deleted; [m-3] E_area numerator wrapped in abs. Compile: 142pp, 0 errors. |
| CHK-024 | CLOSED | fix | PaperCorrector 2 fixes 2026-03-28 (§10 audit): [M-A] parasitic current table corrected (p≈4→p≈2; N=64: 6e-5→2.5e-4, N=128: 4e-6→6.3e-5); [m-B] §\ref{sec:bench_droplet} added. Compile: 142pp. |
| CHK-025 | CLOSED | fix | PaperCorrector 2 fixes 2026-03-28 (§9 audit): [m-A] "1ステップで収束"→"数ステップで減衰（寄生根|ρ₂|=0.5）"; [m-B] "(以下p^m≡δp^m；p^0=0)" added. Compile: 142pp. |
| CHK-026 | CLOSED | fix | PaperCorrector 2 fixes 2026-03-28 (§8 audit): [M-C] p^0=σκ₀→p^0=−σκ₀=σ/R with derivation; [m-D] "確認されている"→"期待される（理論的にはO(h^5)）". Compile: 142pp. |
| CHK-027 | CLOSED | fix | PaperCorrector 2 fixes 2026-03-28 (§1–§7 audit): [F-2] Δτ<εh²→Δτ≤h²/(2ε); [M-1] \texorpdfstring added to 06_grid.tex subsubsection with δ_ε*. Compile: 142pp. |
| CHK-028 | CLOSED | fix | PaperCorrector 1 fix 2026-03-28 (cross-section): [m-A] \epsilon_{\text{norm}}→\varepsilon_{\text{norm}} in 09_full_algorithm.tex:155. Compile: 142pp. |
| CHK-029 | CLOSED | fix | PaperCorrector 1 fix 2026-03-28 (§11 audit): [M-A] 11_conclusion.tex:114 Dissipative CCD O(h^5)→O(ε_d h²). Compile: 142pp. |
| CHK-030 | CLOSED | fix | PaperCorrector 1 fix 2026-03-28 (appendix audit): [M-A] appendix_numerics_solver_s2.tex a₂=3/2→3; 12sin²→24sin²; Λ_max=4.8→9.6. Compile: 142pp. |
| CHK-031 | CLOSED | fix | PaperCorrector 4 fixes 2026-03-28 (full re-audit): [M-A] 10b_benchmarks.tex:321,339,343 Dissipative CCD O(h^5)→O(ε_d h²); [M-B] 08b_ccd_poisson.tex:314–317 Balanced-Force min() argument rewritten. Compile: 142pp, 0 errors, 0 warnings. |
| CHK-032 | CLOSED | review | PaperReviewer full audit 2026-03-28: 3 FATAL all REVIEWER_ERROR; 8 MAJOR: 4 REVIEWER_ERROR + 4 LOGICAL_GAP fixed; 10 MINOR: 5 REVIEWER_ERROR + 5 LOGICAL_GAP fixed (00_abstract:18 DCCD用途追記; 03b:62 O(e^-15)→実質ゼロ; 04b_bc:205 D_0記号除去; 05_advection:229 O(h^6/h)説明追加; 09_algo:56 O(Δt)→厳密値; 11_conc:114 O(εd h²)導出注記). Compile: 142pp, 0 errors, 0 warnings. |
| CHK-033 | CLOSED | review | PaperReviewer full audit 2026-03-28: 0 FATAL; 3 MAJOR 全件REVIEWER_ERROR (M-1: app:cls_fixed_point ラベル+参照は存在; M-2: CLS移流はε_d一定でspace-varying懸念不適用; M-3: ε_d^(i)は局所乗数でcomposition error不発生); 6 MINOR — 未処理(重要度低). 修正ゼロ件. |
| CHK-034 | CLOSED | review+fix | PaperReviewer full audit pass 2 + PaperCorrector 2026-03-28: 0 FATAL; 0 MAJOR; 1 MINOR fixed (02b_csf:225 — 平衡条件 ∇p=σκ∇ψ がu=0でのNS方程式から直接導かれることを1行追記). Compile: 142pp, 0 errors, 0 warnings. |
| CHK-035 | CLOSED | audit | ConsistencyAuditor 全体クロス検証 2026-03-28: AU2 CONDITIONAL FAIL. IMPL_ERR-001: builder.py:148 exp(+φ/ε) vs 論文 exp(-φ/ε) — ψ規約反転; update_properties ψ=1=液(builder規約)で論文式 ρ_l+(ρ_g-ρ_l)ψ と逆; 本番経路自己整合, heaviside()↔update_properties()境界不整合. 10モジュール中8 PASS. 要CodeCorrector. |
| CHK-036 | CLOSED | audit | CodeCorrector IMPL_ERR-001 re-audit 2026-03-28: REVIEWER_ERROR. initial_conditions/builder.py:148 uses exp(+φ/ε) with φ<0=liquid (outward SDF); heaviside.py:52 uses exp(-φ/ε) with φ>0=liquid (paper). Equivalent: φ_builder=−φ_paper. update_properties ρ_l at ψ=1 matches paper Eq.6. curvature.py self-consistent via invert_heaviside. No fix required. 98/98 tests passing. |
| CHK-037 | CLOSED | test | TestRunner full suite 2026-03-28: 98/98 PASS, 0 warnings, 70.73s. CCD d1≥3.5, d2≥2.5, PPE convergence, WENO5, TVD-RK3, Dissipative CCD — all within tolerance (ASM-004). |
| CHK-038 | CLOSED | refactor | CodeReviewer 2026-03-28: 8 LOW_RISK changes applied — R-01 curvature dead code; R-03 magic number comments; R-04 BC loop helper; R-09 viscous sub-method; R-05 ccd_pressure_gradient shared helper; R-06 _pad_neumann→_pad_bc; R-07 _sl module-level; R-02 return annotations. R-08 SKIPPED (§C2 DO NOT DELETE). R-10–R-14 HIGH_RISK deferred. 98/98 PASS. |
| CHK-039 | CLOSED | paper | PaperWriter 2026-03-28: §4d 04d_dissipative_ccd.tex — added 2 new subsubsections: (1) sec:dccd_conservation: flux-form conservation analysis, eq:flux_conservative + eq:flux_filter, DCCD non-conservative acceptability argument vs O(h²) CSF baseline, result:flux_filter_guideline; (2) sec:dccd_pressure_nofilt: pressure filtering prohibition, 2 safe alternatives (∇p filter, PPE RHS regularization), warn:pressure_direct_filter. |
| CHK-040 | CLOSED | compile | PaperCompiler 2026-03-28: XeLaTeX 2-pass clean after CHK-039. 144pp, 0 errors, 0 warnings, 0 undefined refs. Fixed: remarkbox→resultbox; eq:ppe_rhs→eq:rc_divergence. |

## Format reference
`CHK-ID | status: OPEN/IN_PROGRESS/CLOSED | type | location`

────────────────────────────────────────────────────────
# § ASSUMPTIONS

Full detail for each assumption (scope, risk, rationale).

| ASM-ID | Assumption | Scope | Risk | Status |
|---|---|---|---|---|
| ASM-001 | `SimulationBuilder` is the sole construction path — no direct `__init__` construction | `src/twophase/` | HIGH | ACTIVE |
| ASM-002 | PPE Kronecker-product Laplacian has an 8-dimensional null space — `‖Lp−q‖₂` is NOT a valid pass/fail metric | `src/twophase/pressure/` | HIGH | ACTIVE |
| ASM-003 | `"pseudotime"` PPE solver (CCD Laplacian) is the consistent production solver; `"bicgstab"` (FVM matrix) is testing-only and approximate O(h²) | `src/twophase/pressure/` | HIGH | ACTIVE |
| ASM-004 | CCD boundary-limited orders: d1 ≥ 3.5 on L∞ is PASS; d2 ≥ 2.5 on L∞ is PASS — NOT interior O(h⁶)/O(h⁵) | `src/twophase/ccd/` | MEDIUM | ACTIVE |
| ASM-005 | Global PPE sparse system: LGMRES primary, `spsolve` (sparse LU) automatic fallback on non-convergence | `src/twophase/pressure/` | MEDIUM | ACTIVE |
| ASM-006 | Banded/block-tridiagonal systems (CCD Thomas, Helmholtz sweeps): direct LU — O(N) fill-in, efficient | `src/twophase/ccd/` | LOW | ACTIVE |
| ASM-007 | `SimulationConfig` is pure sub-config composition — no monolithic config class | `src/twophase/` | MEDIUM | ACTIVE |
| ASM-008 | Three symmetry-breaking root causes identified and fixed (2026-03-22): (1) Rhie-Chow FVM div at wall node N_ax, (2) PPE gauge pin at center (N/2,N/2), (3) capillary CFL safety factor | `src/twophase/` | HIGH | FIXED |
| ASM-009 | FVM/CCD mismatch in IPC+corrector fixed (2026-03-22): CCD replaced with FD in velocity_corrector.py and predictor.py IPC term | `src/twophase/` | HIGH | FIXED |
| ASM-010 | `docs/00_GLOBAL_RULES.md §P1` is the authoritative LaTeX standard — all paper agents depend on it | `paper/` | MEDIUM | ACTIVE |

## Format reference
`ASM-ID | assumption | scope | risk: HIGH/MEDIUM/LOW | status: ACTIVE/FIXED/DEPRECATED`

────────────────────────────────────────────────────────
# § LESSONS

## §A — Known Error Classes (Mathematical / Code)

| LES-ID | Failure | Cause | Fix Pattern | Reuse Condition |
|---|---|---|---|---|
| KL-01 | Block matrix (2,1) sign flip after RHS transposition | Reading LHS sign directly instead of RHS sign first, then negating | Read RHS coeff → negate → write to LHS. Verify: A_L(2,1)=b₂/h<0, A_R(2,1)=−b₂/h>0 | Any block-matrix entry derived by RHS transposition |
| KL-02 | Wrong block size (3×3 vs 2×2) in documentation | Copy-paste from old 3-variable formulation | Verify block dimensions against actual code arrays | Any block matrix documentation update |
| KL-03 | Pseudocode comment names wrong algorithm (台形則 vs Riemann sum) | Stale comment not updated after algorithm change | Cross-check algorithm name in comment vs. actual accumulation pattern | Any pseudocode with named numerical schemes |
| KL-04 | D(κf) ≠ κD(f) for spatially varying κ | Forgetting Leibniz rule when κ varies in space | Expand D(κf) = κD(f) + f·∇κ — never factor out variable coefficients | Surface tension, variable-density NS, any PDE with spatially varying coefficients |
| KL-05 | Nyquist modified wavenumber ≠ finite-grid spectral radius | Confusing continuous Fourier analysis with finite-grid eigenvalue analysis | Compute spectral radius of actual discrete matrix for finite-N stability bounds | CFL derivation, stability analysis for CCD or compact schemes |
| KL-06 | Pre-asymptotic O(h⁴) convergence mistaken for asymptotic rate | Testing on insufficiently refined grids | Confirm asymptotic regime: slope must stabilize across at least 3 grid doublings | Any convergence order claim from log-log regression |
| KL-07 | "Conservative" CFL rounding in wrong direction | Ceiling instead of floor (or vice versa) | Conservative means SMALLER dt — use floor for dt, ceiling for Nsteps | Any adaptive time-stepping or CFL-limited dt calculation |
| KL-08 | Kronecker product index convention: C-order vs. Fortran-order | NumPy (C-order) Kronecker product gives different index mapping than mathematical convention | State index convention explicitly; verify with N=2 example; match paper's stated convention | Any 2D CCD or Kronecker-product assembly |
| KL-09 | PPE solver design intent: LGMRES-primary / LU-fallback confused with LU-primary | Misreading architecture doc or old code | LGMRES is primary; spsolve is automatic fallback only on LGMRES non-convergence | Any PPE solver configuration or documentation |

## §B — Hallucination Patterns (LaTeX / Paper)

| LES-ID | Failure | Cause | Fix Pattern | Reuse Condition |
|---|---|---|---|---|
| KL-04 | (see §A) — also appears as reviewer claim | Reviewer misapplies product rule | Derive D(κf) from first principles; never accept reviewer claim at face value | Reviewer processing (Reviewer Skepticism Protocol P4) |
| KL-05 | (see §A) — also appears as stability section error | Confusion between Fourier and finite-grid analysis | Independent derivation of spectral radius for N=2 or N=4 | Stability section review |
| KL-06 | (see §A) — also claimed by reviewers as "wrong order" | Pre-asymptotic behavior on coarse grids | Demonstrate asymptotic regime with 4+ grid levels | Convergence claims in paper |
| KL-07 | (see §A) | | | |
| KL-08 | (see §A) | | | |
| KL-10 | Collocated-grid corrector claims exact CCD-divergence-free after projection | RC divergence in PPE RHS leaves residual ∇_RC·u*−D_CCD·u*=O(h²) uncancelled | State ∇_h^RC·u^{n+1}=0 (RC sense); add O(h²) note for CCD sense | Any collocated-grid projection with Rhie-Chow PPE |
| KL-11 | Pin-node exclusion still targets corner (0,0) after pin moved to center (N/2,N/2) | Hardcoded `ravel()[0]` while solver uses dynamic center pin | Replace all hardcoded pin-index references with `pin_dof = ravel_multi_index(tuple(n//2 for n in grid.N), grid.shape)` | Any PPE solver change that moves the gauge pin |
| KL-12 | `\texorpdfstring` missing in numbered heading with math → xelatex hangs 100% CPU | `\section{$O(h^4)$}` without wrapping | Wrap: `\texorpdfstring{$O(h^4)$}{O(h\textasciicircum 4)}` in ALL numbered headings with math; scan before every compile | Every xelatex compile; any numbered heading with `$...$` |

## Format reference
`LES-ID | failure | root cause | fix pattern | when to apply`
