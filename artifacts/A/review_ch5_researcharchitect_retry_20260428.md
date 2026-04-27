# Chapter 5 Strict Review — ResearchArchitect Retry

Date: 2026-04-28
Worktree: `/Users/tomohiro/Downloads/TwoPhaseFlow/.claude/worktrees/worktree-ra-ch5-strict-review-retry`
Branch: `worktree-ra-ch5-strict-review-retry`

## Post-Fix Status

- Fix status: all listed FATAL / MAJOR / MINOR findings addressed in this worktree.
- Files changed: `paper/sections/05_reinitialization.tex`, `paper/sections/05b_cls_stages.tex`, `paper/sections/10d_ridge_eikonal_nonuniform.tex`, `paper/sections/12u4_ridge_eikonal_reinit.tex`.
- Verification: `latexmk -xelatex -interaction=nonstopmode main.tex` completed; `main.pdf` produced at 219 pages. Residual warnings are cosmetic Overfull/Underfull/text-only-float warnings in §12 and existing surrounding material.

## Routing

- ResearchArchitect classification: FULL-PIPELINE
- HAND-01 route: PaperWorkflowCoordinator -> PaperReviewer
- Scope: `paper/sections/05_reinitialization.tex`, `paper/sections/05b_cls_stages.tex`, with targeted checks against §§3, 7, 10, 12, 14 and implementation paths where A3/PR-5 claims required it.
- Verdict: FAIL (2 FATAL, 4 MAJOR, 2 MINOR)

## P4 Reviewer Skepticism Checklist

1. Actual chapter files were read in this turn before citing errors.
2. Each finding below cites a concrete file path, line number, and quoted text.
3. Claims were checked against first principles, supporting paper sections, and implementation/test evidence where applicable.
4. Findings are limited to Chapter 5 and its cited validation/implementation support.
5. PASS criterion is 0 FATAL + 0 MAJOR; current chapter does not meet it.

## FATAL

### F-1 — Final xi-SDF zero-set preservation contradicts mandatory phi-space mass correction

- `paper/sections/05_reinitialization.tex:333`: "`$\phi_\xi$-空間質量補正：`"
- `paper/sections/05_reinitialization.tex:335`: "`$\phi_\xi \leftarrow \phi_\xi + \delta\phi$，`"
- `paper/sections/05_reinitialization.tex:343`: "`命題~1（線形補間零交差の保存）`"
- `paper/sections/05_reinitialization.tex:345`: "`零交差集合 $S_\xi$ 上では $\phi_\xi=0$ であり，`"
- `paper/sections/05_reinitialization.tex:369`: "`命題~3（無反復 $\Rightarrow$ ドリフト累積なし）`"
- `paper/sections/05b_cls_stages.tex:150`: "`drift 蓄積を防ぐため推奨．Stage F は必須であり，主経路では`"

Issue: the xi-SDF algorithm first makes `phi_xi=0` on the interpolated crossing set, but Step 5 then applies a uniform shift `phi_xi <- phi_xi + delta_phi`. For nonzero `delta_phi`, the final `psi` on the original `S_xi` is `H(delta_phi)`, not `0.5`; the final zero set is `{phi_xi = -delta_phi}`. Since §5.2 says Stage F is mandatory on the main path, Proposition 1 and Proposition 3 are false for the final state actually emitted by the algorithm.

Required fix: scope Proposition 1/3 explicitly to the pre-mass-correction distance field, then state the final interface shift bound `|delta_phi|` after Stage F; or make mass correction optional when exact zero-set preservation is the claimed invariant.

### F-2 — Chapter 5 bans psi-curvature in a way that contradicts the paper theorem and implementation

- `paper/sections/05b_cls_stages.tex:172`: "`再初期化前に $\psi$ から曲率計算`"
- `paper/sections/05b_cls_stages.tex:173`: "`symmetric tanh profile の曲率は最大 $\mathcal{O}(1/\varepsilon)$`"
- `paper/sections/05b_cls_stages.tex:175`: "`$\phi$ から $\mathbf{n}=\bnabla\phi/|\bnabla\phi|$，`"
- `paper/sections/03c_levelset_mapping.tex:84`: "`曲率は $\phi$ と $\psi$ のいずれから計算しても同一`"
- `paper/sections/02c_nondim_curvature.tex:191`: "`レベルセット曲率の単調変換不変性`"
- `src/twophase/levelset/curvature_psi.py:43`: "`class CurvatureCalculatorPsi(ICurvatureCalculator):`"

Issue: the failure-mode paragraph broadly states that computing curvature from `psi` overestimates curvature by `O(1/epsilon)` and instructs use of `phi`. This contradicts the monotone-reparameterization theorem in §2/§3 and the implemented/recommended `CurvatureCalculatorPsi` path. A tanh profile alone does not create `O(1/epsilon)` curvature error when using the normalized invariant formula; only naive/un-normalized `psi` derivatives or distorted non-monotone profiles would.

Required fix: narrow the warning to the actual forbidden operation, e.g. naive `laplacian(psi)` or curvature evaluation outside the monotone interface band, and align Stage E with the chosen curvature pipeline (`psi` direct, `phi` direct, or HFE-specific).

## MAJOR

### M-1 — Single-step mass correction is presented as exact closure

- `paper/sections/05_reinitialization.tex:271`: "`質量保存（前クリッピング）`"
- `paper/sections/05_reinitialization.tex:273`: "`$\sum\psi_{\mathrm{corr}}=\sum\psi_{\mathrm{old}}$ が成立する`"
- `paper/sections/05b_cls_stages.tex:117`: "`= \operatorname{clip}_{[0,1]}\!`"
- `paper/sections/05b_cls_stages.tex:135`: "`M_\text{target}-\sum_i H_\varepsilon(\phi_i)V_i`"
- `src/twophase/levelset/reinit_eikonal.py:153`: "`delta_phi = gate * (M_old - M_new) / W_safe`"
- `src/twophase/tests/test_levelset.py:688`: "`preserves volume to <0.5%`"

Issue: `delta_phi = Delta M / integral H'_epsilon dV` is one Newton/linearized update for a nonlinear mass functional. It gives exact closure only in the infinitesimal/linearized case or if iterated to convergence. The psi-space formula also clips after applying the correction, so equality is not guaranteed after saturation. The tests use tolerance language (`<0.5%`, `<1e-4`), not exact equality.

Required fix: replace exact-equality language with "first-order/Newton correction; residual monitored to tolerance", or specify an iterative root solve if exact closure is intended.

### M-2 — Fallback pseudo-time stability rule mixes Godunov/WENO-HJ with old compression-diffusion CFL

- `paper/sections/05_reinitialization.tex:412`: "`以下の $\Delta\tau$ と停止条件は，`"
- `paper/sections/05_reinitialization.tex:413`: "`Godunov/WENO--HJ 型の反復 Eikonal solver を fallback として選ぶ場合にのみ適用する．`"
- `paper/sections/05_reinitialization.tex:415`: "`2 次元拡散安定限界`"
- `paper/sections/07_time_integration.tex:987`: "`圧縮項と拡散項をともに陽的に扱う場合の参考安定条件`"
- `paper/sections/07_time_integration.tex:990`: "`旧実装（\S~\ref{sec:dissipative_ccd}，§4.4）との比較参照`"

Issue: §5 says the diffusion-limit `Delta tau` guidance applies to iterative Godunov/WENO-HJ Eikonal fallback, while §7 defines that limit as a reference for the old explicit compression-diffusion reinitialization equation. A Hamilton-Jacobi Eikonal solver and the old compression-diffusion CLS equation have different stability constraints.

Required fix: split the implementation guide into two fallback families: HJ Eikonal (`Delta tau` CFL for Godunov/WENO-HJ) and legacy compression-diffusion (hyperbolic + parabolic CFL from §7).

### M-3 — Calibration/validation references do not contain the claimed data

- `paper/sections/05_reinitialization.tex:129`: "`既定値の選定および感度は §~\ref{sec:val_summary} を参照`"
- `paper/sections/05_reinitialization.tex:244`: "`反復回数は §~\ref{sec:val_summary} 参照`"
- `paper/sections/05_reinitialization.tex:389`: "`$f$ の選定および $f{=}1$ との性能差は`"
- `paper/sections/05_reinitialization.tex:390`: "`§~\ref{sec:val_capillary} で定量比較`"
- `paper/sections/14_benchmarks.tex:87`: "`$\varepsilon_\text{scale}=1.4$`"
- `paper/sections/14_benchmarks.tex:99`: "`毛管波動力学の定量 validation は ... 再実行後に確定`"

Issue: §5 points readers to §14 for `theta_reinit`, pseudo-time iteration counts, and `f=1` vs `f>1` performance. The cited benchmark section only states `epsilon_scale=1.4` and explicitly says the capillary-wave quantitative dynamics are not yet validated with the current saved data. The `val_summary` table also does not list `theta_reinit` or `N_tau,max`.

Required fix: redirect iteration-count support to U4 if that is the intended evidence, add the missing parameter sweep for `theta_reinit` and `f`, or downgrade the claims to design choices with unvalidated status.

### M-4 — CCD zero-sum proof uses an invalid implication

- `paper/sections/05_reinitialization.tex:81`: "`連立方程式 $A\bm{x} = \bm{b}$ の $\bm{b}$ が零和であり $A$ が正則であるから，`"
- `paper/sections/05_reinitialization.tex:82`: "`$\sum_i d_{1,i} = 0$，$\sum_i d_{2,i} = 0$ が厳密に成立する`"

Issue: nonsingularity of `A` does not by itself preserve the zero-sum subspace. The conclusion may be true for periodic compact matrices, but it requires the constant-vector/column-sum property of the specific periodic CCD matrix, not mere invertibility.

Required fix: replace the proof with `1^T A = c 1^T` (or the equivalent periodic row/column-sum statement), then derive `c sum_i x_i = sum_i b_i = 0`.

## MINOR

### m-1 — Supporting A3 path in U4 points to obsolete implementation locations

- `paper/sections/12u4_ridge_eikonal_reinit.tex:92`: "`§\ref{sec:eikonal_reinit} 離散化 →`"
- `paper/sections/12u4_ridge_eikonal_reinit.tex:93`: "`\texttt{src/twophase/cls/reinit.py}`"
- `paper/sections/12u4_ridge_eikonal_reinit.tex:95`: "`\texttt{src/twophase/cls/dgr.py}`"

Issue: the actual implementation lives under `src/twophase/levelset/`, so the validation support for §5 is not A3-resolvable as written.

Required fix: update U4 A3 paths to `src/twophase/levelset/reinit_eikonal.py`, `src/twophase/levelset/reinit_dgr.py`, and/or `src/twophase/levelset/ridge_eikonal_reinitializer.py`.

### m-2 — Stale source comments still expose obsolete file/history names

- `paper/sections/05_reinitialization.tex:61`: "`% §10_full L312 ref 保護`"
- `paper/sections/10d_ridge_eikonal_nonuniform.tex:1`: "`% paper/sections/06d_ridge_eikonal_nonuniform.tex`"
- `paper/sections/10d_ridge_eikonal_nonuniform.tex:3`: "`% §9.5  Ridge–Eikonal の非一様格子実装`"

Issue: comments are not visible in PDF, but they are stale and undermine maintainability during later review passes.

Required fix: refresh comments to current filenames/section numbers or remove them when they only preserve historical context.

## Recommended Fix Order

1. F-1: decide invariant priority for xi-SDF final state (zero set vs mass closure), then rewrite Proposition 1/3 and Stage F wording.
2. F-2: align Stage E curvature guidance with §2/§3 theorem and `CurvatureCalculatorPsi`.
3. M-1: demote exact mass closure to tolerance/Newton wording or implement/document iterative solve.
4. M-2: separate HJ fallback stability from legacy compression-diffusion CFL.
5. M-3/m-1: repair validation/A3 support references.
6. M-4/m-2: clean proof wording and stale comments.
