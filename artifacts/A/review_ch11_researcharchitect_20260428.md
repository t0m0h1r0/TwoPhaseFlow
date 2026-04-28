# Chapter 11 Strict Review — ResearchArchitect

Date: 2026-04-28
Worktree: `/Users/tomohiro/Downloads/TwoPhaseFlow-ch11-review`
Branch: `worktree-ra-ch11-review`

## Post-Fix Status

- Fix status: all listed FATAL / MAJOR / MINOR findings addressed in this worktree.
- Fix commits: `d296568` (chapter numbering), `d07bdd3` (paper U-test evidence), `0e39d36` (verification scripts / paper figure regeneration path).
- Verification completed before closure: targeted stale-pattern grep, Python syntax check for all U1--U9 scripts, and LaTeX build.

## Routing

- ResearchArchitect classification: FULL-PIPELINE
- HAND-01 route: PaperWorkflowCoordinator -> PaperReviewer
- Scope: current Chapter 11 as compiled from `paper/main.tex`, i.e. `paper/sections/12_component_verification.tex` and `paper/sections/12u*.tex`. The old `paper/sections/11_full_algorithm.tex` was removed by CHK-246.
- Verdict: FAIL (4 FATAL, 5 MAJOR, 2 MINOR)

## Reviewer Skepticism Checklist

1. The current chapter identity was checked from `paper/main.tex`, not inferred from filename prefixes.
2. Each finding cites concrete source lines and the implementation or experiment evidence used to reject the claim.
3. Findings are limited to current Chapter 11 and the roadmap / scripts / code paths it directly cites.
4. PASS criterion is 0 FATAL + 0 MAJOR; current Chapter 11 does not meet it.

## FATAL

### F-1 — Chapter 11 is structurally inconsistent after old §11 removal

- `paper/main.tex:92`: old §11 is declared completely removed by CHK-246.
- `paper/main.tex:95`: `12_component_verification` is still commented as `§12`, but it is the next `\section` after §10 and therefore compiles as current Chapter 11.
- `paper/sections/12_component_verification.tex:3`: file header still says `§12`.
- `paper/sections/12_component_verification.tex:41`: the chapter says it verifies primitives from an algorithm construction already presented in the paper.
- `paper/sections/01b_classification_roadmap.tex:186`: the roadmap still lists chapter 10 as "完全アルゴリズム", even though current chapter 10 is grid.

Issue: the chapter under review is current Chapter 11, but its filenames, comments, roadmap dependencies, and stated predecessor chapter still reflect a pre-CHK-246 structure. A reviewer cannot tell whether Chapter 11 is the component-verification chapter or a missing complete-algorithm chapter without inspecting `main.tex`.

Required fix: renumber or explicitly document the post-CHK-246 structure everywhere visible to readers: roadmap table, comments, chapter prose, appendix comments, and any "§12" support text for this chapter.

### F-2 — A3 traceability is broken by nonexistent implementation paths

- `paper/sections/12u5_heaviside_delta.tex:92`: points to `src/twophase/utils/heaviside.py`, which does not exist.
- `paper/sections/12u6_split_ppe_dc_hfe.tex:122`: points to `src/twophase/ppe/split_solver.py`, which does not exist.
- `paper/sections/12u6_split_ppe_dc_hfe.tex:124`: points to `src/twophase/ppe/hfe.py`, which does not exist.
- `paper/sections/12u7_bf_static_droplet.tex:100`: points to `src/twophase/coupling/bf.py`, which does not exist.
- `paper/sections/12u7_bf_static_droplet.tex:102`: points to `src/twophase/coupling/face_interp.py`, which does not exist.
- `paper/sections/12u8_time_integration.tex:125`: points to `src/twophase/time/rk.py`, which does not exist.
- `paper/sections/12u8_time_integration.tex:128`: points to `src/twophase/time/cn_adi.py`, which does not exist.
- `paper/sections/12u9_dccd_pressure_prohibition.tex:83`: points to `src/twophase/ccd/dccd_solver.py`, which does not exist.

Issue: Chapter 11 explicitly claims A3 "Equation -> Discretization -> Code" traceability, but many code endpoints are stale or fabricated relative to the current source tree. This is a direct A3 failure, not a cosmetic path issue.

Required fix: replace all A3 endpoints with existing implementation paths, or remove the A3 claim for subtests whose current scripts are standalone verification kernels rather than paper-code equivalence checks.

### F-3 — U6 claims split-PPE verification, but the script tests lumped PPE only

- `paper/sections/12u6_split_ppe_dc_hfe.tex:8`: subsection title is `Split-PPE + DC + HFE`.
- `paper/sections/12u6_split_ppe_dc_hfe.tex:12`: verification target is the split-PPE pressure system.
- `experiment/ch12/exp_U6_split_ppe_dc_hfe.py:2`: script title is `Lumped PPE + DC + HFE`.
- `experiment/ch12/exp_U6_split_ppe_dc_hfe.py:12`: script says split rescue is verified end-to-end in later high-density simulations, not here.
- `experiment/ch12/exp_U6_split_ppe_dc_hfe.py:221`: solver config uses `phase_density`.
- `experiment/ch12/exp_U6_split_ppe_dc_hfe.py:265`: U6-b also uses `phase_density`.

Issue: the central Tier IV claim is mislabeled. The chapter says U6 verifies split-PPE, but the executable evidence is a lumped/phase-density FCCD-PPE stress test. That invalidates the PR-5 link for U6 as written.

Required fix: retitle U6 as lumped-PPE/DC/HFE limitation evidence, or implement and report a genuine split-PPE unit test in this chapter.

### F-4 — U7 match/mismatch interpretation contradicts the script

- `paper/sections/12u7_bf_static_droplet.tex:21`: match is described as same density inside/outside.
- `paper/sections/12u7_bf_static_droplet.tex:22`: mismatch is described as `rho_l/rho_g = 10`.
- `experiment/ch12/exp_U7_bf_static_droplet.py:54`: global `RHO_L = 1000.0`.
- `experiment/ch12/exp_U7_bf_static_droplet.py:104`: both modes use the same density field.
- `experiment/ch12/exp_U7_bf_static_droplet.py:109`: `match` changes only the `grad psi` operator to CCD.
- `experiment/ch12/exp_U7_bf_static_droplet.py:114`: `mismatch` changes only the `grad psi` operator to FD2.

Issue: U7 is presented as a density-ratio match/mismatch experiment, but the script actually tests operator pairing mismatch at fixed high density ratio. The reported table cannot support the text's density-ratio conclusion.

Required fix: rewrite U7-a as a discrete-gradient pairing test, or add separate density-ratio cases with explicit `rho_l/rho_g` control.

## MAJOR

### M-1 — U5 moment definitions are not the quantities the script computes

- `paper/sections/12u5_heaviside_delta.tex:19`: U5-a says it tests `H_eps` zeroth moment.
- `paper/sections/12u5_heaviside_delta.tex:20`: formula uses `sum H_eps(phi_i) h - 1`.
- `paper/sections/12u5_heaviside_delta.tex:21`: first moment uses `sum H_eps(phi_i) phi_i h - 1/2`.
- `experiment/ch12/exp_U5_heaviside_delta_accuracy.py:58`: script computes `delta_vals = delta(...)`.
- `experiment/ch12/exp_U5_heaviside_delta_accuracy.py:59`: zeroth moment is `sum(delta_vals) h`.
- `experiment/ch12/exp_U5_heaviside_delta_accuracy.py:60`: first moment is `sum(x * delta_vals) h`.
- `src/twophase/levelset/heaviside.py:43`: implementation is logistic Heaviside, not the cosine-window wording in `paper/sections/12u5_heaviside_delta.tex:85`.

Issue: the paper describes Heaviside integrals, while the script measures delta-function moments. The two are not interchangeable, and the stated formula would not reproduce the table.

Required fix: rewrite U5 formulas as delta moment tests and align the smoothing-kernel description with `src/twophase/levelset/heaviside.py`.

### M-2 — U8-d is simultaneously marked degraded and fully passing

- `paper/sections/12_component_verification.tex:120`: parent summary marks U8-d as conditional pass with measured slope `1.0`.
- `paper/sections/12u8_time_integration.tex:78`: U8-d caption says all layers have slope approximately `2.0`.
- `paper/sections/12u8_time_integration.tex:95`: the table reports B/C slopes of `1.00`.
- `paper/sections/12u8_time_integration.tex:120`: evaluation says B/C degrade to effective first order.
- `paper/sections/12u8_time_integration.tex:122`: the same bullet ends with `\checkmark`.
- `experiment/ch12/exp_U8_time_integration_suite.py:224`: script expects Layer B first order.
- `experiment/ch12/exp_U8_time_integration_suite.py:227`: script expects Layer C around 1.5 order, but reported table has 1.00.

Issue: the chapter gives three different verdicts for the same subtest: design second order, known first-order degradation, and full checkmark. This makes the Tier V verdict non-auditable.

Required fix: classify U8-d as conditional/known degradation consistently, or modify the method/test until B/C reach the stated design target.

### M-3 — U9 paper text does not match the negation script

- `paper/sections/12u9_dccd_pressure_prohibition.tex:19`: paper says `p = sin(pi x) sin(pi y)`.
- `experiment/ch12/exp_U9_dccd_pressure_prohibition.py:107`: script uses `sin(2*pi x) sin(2*pi y)`.
- `paper/sections/12u9_dccd_pressure_prohibition.tex:22`: paper frames the baseline as `grad p`.
- `experiment/ch12/exp_U9_dccd_pressure_prohibition.py:108`: script measures the Laplacian.
- `paper/sections/12u9_dccd_pressure_prohibition.tex:36`: caption says ratio diverges exponentially as `h -> 0`.
- `paper/sections/12u9_dccd_pressure_prohibition.tex:47`: table ratio decreases from `6.55e7` at N=128 to `3.86e7` at N=256.

Issue: the negation test may still be useful, but the paper's mathematical object, manufactured solution frequency, and asymptotic description are inconsistent with the executable script and its own table.

Required fix: align U9 to the Laplacian test actually run, or implement the stated gradient test. Replace "exponential divergence" with the measured algebraic/floor-limited behavior.

### M-4 — U1-c's conditional-pass rationale contradicts its script

- `paper/sections/12u1_ccd_operator.tex:76`: caption calls U1-c `FCCD periodic face value/grad`.
- `paper/sections/12u1_ccd_operator.tex:77`: the same caption attributes the fourth-order result to wall boundary conditions.
- `paper/sections/12u1_ccd_operator.tex:93`: footnote again says wall-boundary fourth-order endpoint effects dominate.
- `experiment/ch12/exp_U1_ccd_operator_suite.py:121`: script constructs `FCCDSolver(..., bc_type="periodic")`.

Issue: the measured fourth-order FCCD result is explained by a wall-boundary mechanism that is not present in the script. The conditional pass may be valid, but its explanation is unsupported.

Required fix: either change the U1-c experiment to wall BC or explain the actual periodic-grid mechanism behind the fourth-order measurement.

### M-5 — Reproducibility path for figures is not one-command traceable

- `paper/sections/12_component_verification.tex:78`: chapter says U-tests write `data.npz` and representative PDF figures under `experiment/ch12/results/U<i>_<name>/`.
- `paper/sections/12u1_ccd_operator.tex:99`: paper includes `figures/ch12_u1_ccd_operator_suite`.
- `src/twophase/tools/experiment/figure.py:42`: `save_figure` can write a secondary destination via `also_to`.
- `experiment/ch12/exp_U1_ccd_operator_suite.py:220`: script saves only to the experiment results directory.
- `experiment/ch12/exp_U8_time_integration_suite.py:429`: same pattern; no script passes `also_to=paper/figures/...`.

Issue: the committed paper figures live in `paper/figures/ch12_u*.pdf`, but the stated scripts only regenerate `experiment/ch12/results/.../*.pdf`. A reviewer cannot regenerate the paper figures in place by running the cited U-tests.

Required fix: pass `also_to` for each paper figure, or document a controlled copy/sync step and commit its command.

## MINOR

### m-1 — Parent summary count is arithmetically wrong

- `paper/sections/12_component_verification.tex:99`: U1-a is a checkmark.
- `paper/sections/12_component_verification.tex:121`: U9 is the only bullet negation row.
- `paper/sections/12_component_verification.tex:126`: summary says `17 checkmark + 3 triangle + 1 bullet`.

Issue: the table actually contains 19 checkmarks, 3 conditional triangles, and 1 bullet. The summary undercounts successful subtests by two.

Required fix: recount the table after deciding whether U8-d remains a checkmark or conditional result.

### m-2 — Script docstrings still cite pre-renumbered §12 support files

- `experiment/ch12/exp_U1_ccd_operator_suite.py:4`: paper ref says `§12.1.1`.
- `experiment/ch12/exp_U3_nonuniform_spatial_suite.py:4`: refers to `12c_spatial_geometry.tex`.
- `experiment/ch12/exp_U4_ridge_eikonal_reinit.py:4`: refers to `12d_interface_pipeline.tex`.
- `experiment/ch12/exp_U6_split_ppe_dc_hfe.py:4`: refers to `12e_interface_field.tex`.

Issue: these are not necessarily PDF-visible, but they make the chapter's support material harder to audit after the current chapter-number shift and §12 rewrite.

Required fix: refresh docstrings to current section labels and active `12u*.tex` files.

## Recommended Fix Order

1. Fix chapter identity and roadmap numbering after CHK-246.
2. Repair A3 code endpoints or explicitly downgrade unsupported A3 claims.
3. Resolve U6/U7/U5/U9 paper-script mismatches before using their verdicts.
4. Normalize U8-d and U1-c verdict language.
5. Add a paper-figure regeneration path or document the copy step.
6. Recount the parent dashboard and clean stale script docstrings.
