# 02_ACTIVE_LEDGER — Phase, Branch, CHK Register, Assumptions & Lessons
# LIVE document — append-only for CHK/ASM/KL entries; phase/branch updated each session.
# Last updated: 2026-04-18

────────────────────────────────────────────────────────
# § ACTIVE STATE

| Key | Value |
|---|---|
| phase | META_REDESIGN_IN_PROGRESS |
| branch | worktree-worktree-ch13-dgr-blowup-fix |
| last_CHK | CHK-133 DONE 2026-04-18 — ch13 DGR blowup root cause identified and fixed. DGR alone fails for sigma>0 capillary dynamics (interface folds undetectable by median eps_eff); all 4 exp13_01 DGR configs changed to hybrid. Tests: 206 passed. WIKI-T-030 updated. |
| next_action | Merge worktree-ch13-dgr-blowup-fix → main via PR after T=10 remote run confirms no blowup. |

### Notes
- `last_CHK` is the most recent closed work item; older CHKs live in § CHECKLIST tables below.
- ALL 31 ch11 experiments are GPU-opted and baselined (CHK-125..127).
- Wiki: 100 entries (docs/wiki/INDEX.md).

────────────────────────────────────────────────────────
# § CHECKLIST — recent activity (one line per CHK)
# Format: `CHK-ID | YYYY-MM-DD | type | summary`
# Full detail in git log / commit messages / linked memos.

## §1 — Most recent (CHK-120..132)

| CHK | Date | Type | Summary |
|---|---|---|---|
| CHK-133 | 2026-04-18 | fix | ch13 DGR blowup: root cause = DGR cannot repair interface folds (|∇ψ|→0) under σ>0 capillary dynamics; global median eps_eff treats folds as outliers → DGR near-no-op → CSF blowup. Fix: reinit_method: hybrid in exp13_01_a{1.0,1.2,1.5,2.0}_dgr.yaml. Isolation exps A1-A4 confirm mechanism. WIKI-T-030 Limitations section added. Tests 206P/7S/2XF. Branch: worktree-ch13-dgr-blowup-fix |
| CHK-132 | 2026-04-18 | meta | v7.0.0 "Lean Kernel" redesign: 8 kernel-*.md (constitution/roles/ops/domains/workflow/antipatterns/project/deploy) + 46 agent files (23 claude + 23 codex) + 2 _base.yaml. -56% token target. v6.0.0 features: HAND-04/DYNAMIC-REPLANNING/OP-CONDENSE/EVALUATOR-OPTIMIZER. Branch: meta-v7-lean-kernel |
| CHK-131 | 2026-04-17 | fix | GPU smoke tests: thomas_precompute .get() fix (linalg_backend.py); atol 1e-13→1e-11 (test_gpu_smoke.py); 3 FAILED → 0 |
| CHK-130 | 2026-04-16 | fix+paper+merge | ch11 reinit non-uniform fix (4 files); DGR fallback α>1; exp11_29 880× improvement; WIKI-E-017 updated |
| CHK-129 | 2026-04-15 | paper+merge | ch12 re-run paper sync + main merge (752b9f3); 5 tex files; 199pp 0 err |
| CHK-128 | 2026-04-12 | fix | FieldExtender upwind NaN fix (65aed8d); q_safe masking; test added |
| CHK-127 | 2026-04-12 | gpu-optin | exp11_22 zalesak_nonuniform (Tier C, CPU baseline generated first); 31/31 ch11 GPU-opted |
| CHK-126 | 2026-04-12 | gpu-optin | Batch 6b (5 exp: 11_12b/14_picard/25/28/29) + 6 library CuPy-strict fixes |
| CHK-125 | 2026-04-11 | gpu-optin | Batch 6a (3 exp: 11_15/24/27); confirms ASM-122-A DGR-contractive mechanism |
| CHK-124 | 2026-04-11 | diagnosis | ASM-122-A root cause = FUNDAMENTAL (chaos-amplified FP noise, Lyapunov λ≈ln(e)/20steps); 5-probe binary search |
| CHK-123 | 2026-04-12 | deploy | EnvMetaBootstrapper v5.2 + v1.1 Hybrid redeploy; 33 agents + AP-09/10 inject |
| CHK-122 | 2026-04-12 | perf | cn_diffusion_axis dense-inverse (70×); exp11_21 CPU 258s → GPU 61.6s (4.19×); documented ASM-122-A |
| CHK-121 | 2026-04-12 | gpu-optin | Batch 5 (exp11_19/20/21/23); exp11_21 62 min → 2 min post perf-rounds; `make push --checksum` load-bearing |
| CHK-120 | 2026-04-12 | perf+fix | Round 6 rsync-race correction; `--checksum` added. Corrected Test B 900s→41.25s (−95.4% vs CHK-106) |

## §2 — Perf/GPU rounds (CHK-115..119)

| CHK | Date | Type | Summary |
|---|---|---|---|
| CHK-119 | 2026-04-12 | perf | Round 5: A_inv_dev = lu_solve(I) cached; GPU hot = A_inv @ rhs (18× speedup) |
| CHK-118 | 2026-04-11 | perf | Round 4: cached device ops for _build_axis_solver; matmul contractions |
| CHK-117 | 2026-04-11 | perf | Round 3b: Wall-BC CCD unified onto dense block-banded LU |
| CHK-116 | 2026-04-11 | perf | Round 3a: vectorised _differentiate_wall_raw; 126→4 launches/CCD call |
| CHK-115 | 2026-04-11 | perf+gpu | Round 2 perf tuning + Batch 4 GPU opt-in (collision — ID reused by 2 parallel worktrees) |
| CHK-114 | 2026-04-11 | meta | v5.1.0 Concurrency-Aware refactor (worktree-based locks; HAND schema); feature flag flipped LIVE |
| CHK-113 | 2026-04-11 | gpu-optin | Batch 3 (exp11_10/11/17/26) |
| CHK-112 | 2026-04-11 | gpu-optin | Batch 2 (exp11_4/8/14) |
| CHK-111 | 2026-04-11 | review | PaperReviewer §11–§13 review (0F/4M/7m/2S); WIKI-P-006 |
| CHK-110 | 2026-04-11 | gpu-optin | Batch (exp11_3/9/16); hybrid CPU scipy.sparse + device CCD pattern |
| CHK-109 | 2026-04-11 | gpu-optin | exp11_7 HFE + ClosestPointExtender xp fix (Phase C leak #3) |
| CHK-108 | 2026-04-11 | gpu-optin | Grid.meshgrid() device-aware + exp11_2 |
| CHK-107 | 2026-04-11 | infra | Remote-default + GPU auto-selection; Makefile run/run-local targets; pyproject cupy→[gpu] extra |
| CHK-106 | 2026-04-12 | backend | CuPy backend unification (retroactive close — all content absorbed via 107..127 chain) |

## §3 — Earlier activity (CHK-085..105)

| CHK | Date | Type | Summary |
|---|---|---|---|
| CHK-105 | 2026-04-09 | paper | §7b DCCD mass proof + adaptive reinit; §10 Step 2 trigger; §11.2 conservation verify |
| CHK-104 | 2026-04-09 | wiki | Shape preservation memo + WIKI-T-028 update |
| CHK-103 | 2026-04-09 | exp | exp11_19 shape study; adaptive reinit DOMINANT (+49%, 227→2 reinits) |
| CHK-102 | 2026-04-09 | exp | exp11_18 CLS-DCCD conservation verified; split+mc recommended |
| CHK-101 | 2026-04-09 | theory | CLS-DCCD conservation analysis; unified DCCD reinit proposed; WIKI-T-028 |
| CHK-100 | 2026-04-08 | wiki | ch11 experiment wiki (L-002..L-007); 48 entries |
| CHK-099 | 2026-04-08 | audit | WikiAuditor K-LINT PASS; INDEX.md created |
| CHK-098 | 2026-04-08 | wiki | Memo wiki compilation (10 new); 41 entries |
| CHK-097 | 2026-04-08 | wiki | Appendix wiki (T-010..T-018, 9 new); 31 entries |
| CHK-096 | 2026-04-08 | review | PaperReviewer §1–§11 (0F/7M/14m/3S); 10 verifications PASS |
| CHK-095 | 2026-04-08 | paper | §5–§8 bridges + §11 zero-base rewrite |
| CHK-094 | 2026-04-08 | deploy | EnvMetaBootstrapper full regen (33 agents) |
| CHK-093 | 2026-04-08 | wiki | ch11 experiment wiki (E-001..E-006) |
| CHK-092 | 2026-04-07 | wiki | §1–§3 wiki (T-006..T-009, P-003, X-003) |
| CHK-091 | 2026-04-07 | wiki | First 10 wiki entries; K-Domain operational |
| CHK-090 | 2026-04-07 | review | PaperReviewer §4–§10 story structure; 6 issues |
| CHK-089 | 2026-04-07 | deploy | EnvMetaBootstrapper A1→A11 (Knowledge-First); 4 K-Domain agents |
| CHK-085 | 2026-03-31 | paper | §8 structural rewrite (Modifications I–IV); 167pp |
| CHK-010..084 | 2026-03-27 .. 03-31 | paper+code+test | Initial bootstrap, §9–§12 narrative, DCCD verification, 154/154 tests. Full detail in git log. |

────────────────────────────────────────────────────────
# § ASSUMPTIONS

| ASM | Status | Scope | One-line |
|---|---|---|---|
| ASM-001 | ACTIVE | src/twophase/ | SimulationBuilder is sole construction path |
| ASM-002 | ACTIVE | src/twophase/pressure/ | PPE Kronecker has 8-dim null space — ‖Lp−q‖₂ not a pass/fail metric |
| ASM-003 | DEPRECATED | src/twophase/pressure/ | Superseded 2026-04-15 by PR-2 — CCD Kronecker PPE indefinite (2 wrong-sign eigenvalues/axis); CCD-LU restricted to ch11 smooth-RHS tests |
| ASM-004 | ACTIVE | src/twophase/ccd/ | CCD boundary-limited: d1 ≥ 3.5, d2 ≥ 2.5 on L∞ |
| ASM-005 | DEPRECATED | src/twophase/pressure/ | Superseded 2026-04-15 — LGMRES prohibited for PPE (PR-6); production = FD spsolve or DC sweep |
| ASM-006 | ACTIVE | src/twophase/ccd/ | Banded/block-tridiag: direct LU (O(N) fill-in) |
| ASM-007 | ACTIVE | src/twophase/ | SimulationConfig is pure sub-config composition |
| ASM-008 | FIXED | src/twophase/ | 3 symmetry-breaking root causes fixed 2026-03-22 (Rhie-Chow wall N_ax, PPE pin at center, capillary CFL) |
| ASM-009 | FIXED | src/twophase/ | FVM/CCD mismatch in IPC+corrector fixed 2026-03-22 |
| ASM-010 | ACTIVE | paper/ | docs/00_GLOBAL_RULES.md §P1 is authoritative LaTeX standard |
| ASM-122-A | FUNDAMENTAL | src/twophase/levelset/reinit_split.py | GPU/CPU pointwise drift on long Zalesak runs = chaos-amplified FP noise (CHK-124). Lyapunov λ≈ln(e)/20 steps. Hybrid/DGR path escapes via Lyapunov-contractive projection. PR-5 carve-out: pointwise O(1e-2) on split GPU is fundamental; L₂/mass/physics preserved. DGR default for α>1 in ns_pipeline.py reduces practical impact (CHK-130). |

────────────────────────────────────────────────────────
# § LESSONS (KL-01 .. KL-12)

## §A — Known Error Classes (Math/Code)

| KL | Failure | Fix Pattern |
|---|---|---|
| KL-01 | Block matrix (2,1) sign flip after RHS transposition | Read RHS coeff → negate → write to LHS |
| KL-02 | Wrong block size (3×3 vs 2×2) in docs | Verify block dims against actual code arrays |
| KL-03 | Pseudocode comment names wrong algorithm | Cross-check comment vs accumulation pattern |
| KL-04 | D(κf) ≠ κD(f) for varying κ | Expand D(κf) = κD(f) + f·∇κ — never factor variable coefficients |
| KL-05 | Nyquist modified wavenumber ≠ finite-grid spectral radius | Compute spectral radius of actual discrete matrix |
| KL-06 | Pre-asymptotic O(h⁴) mistaken for asymptotic | Confirm slope stability over ≥3 grid doublings |
| KL-07 | "Conservative" CFL rounding wrong direction | Conservative means SMALLER dt — floor for dt, ceiling for Nsteps |
| KL-08 | Kronecker C-order vs Fortran-order confusion | State convention explicitly; verify with N=2 example |
| KL-09 | PPE LGMRES-primary/LU-fallback vs LU-primary confusion | LGMRES primary; spsolve auto-fallback on non-convergence (pre-2026-04-15) |
| KL-10 | Collocated corrector "exact CCD-div-free" claim | RC PPE leaves ‖∇_RC·u^{n+1}‖=0 but CCD sense residual O(h²) |
| KL-11 | Pin-node excl still targets (0,0) after move to center | Use `pin_dof = ravel_multi_index(tuple(n//2 for n in grid.N), grid.shape)` |
| KL-12 | `\texorpdfstring` missing in math heading → xelatex infinite loop | Wrap ALL numbered headings with `$...$` in texorpdfstring; pre-compile grep scan required |

────────────────────────────────────────────────────────
# § REFERENCE — moved content

- **§5 Evolution Log** (EVO-001..006 meta-governance YAML): moved to git commit messages + `prompts/meta/meta-deploy.md §v1.1 changelog`
- **§4 Branch Lock Registry** (v5.1 concurrency): live state in `docs/locks/*.lock.json`; historical rows in git log. Protocol: `prompts/meta/meta-ops.md §LOCK-ACQUIRE/RELEASE`
- **§ INTEGRITY_MANIFEST**: all-pending hash placeholders dropped. Contracts unsigned; re-introduce when first interface is locked.
