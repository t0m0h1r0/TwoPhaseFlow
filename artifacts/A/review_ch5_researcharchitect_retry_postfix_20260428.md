# Chapter 5 Post-Fix Re-Review — ResearchArchitect Retry

Date: 2026-04-28
Worktree: `/Users/tomohiro/Downloads/TwoPhaseFlow/.claude/worktrees/worktree-ra-ch5-strict-review-retry`
Branch: `worktree-ra-ch5-strict-review-retry`

## Scope

- Re-reviewed the post-fix state of `paper/sections/05_reinitialization.tex` and `paper/sections/05b_cls_stages.tex`.
- Targeted cross-checks: `paper/sections/10d_ridge_eikonal_nonuniform.tex`, `src/twophase/levelset/reinit_eikonal.py`, `src/twophase/levelset/ridge_eikonal_reinitializer.py`.
- Build status after follow-up fix: `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` completed, 219 pages.

## Verdict

PASS after follow-up fix: 0 FATAL, 0 MAJOR, 0 MINOR.

The previous FATAL items are resolved. The post-fix A3/PR-5 mismatch in the generic Stage F mass-closure equation for nonuniform/local-epsilon Ridge--Eikonal paths was fixed by making Stage F local-epsilon aware.

## Resolved Follow-up Finding

### Resolved M-1 — Stage F mass-closure equation was scalar-epsilon, but nonuniform Ridge--Eikonal uses local epsilon

- `paper/sections/05b_cls_stages.tex:132`: Stage F now uses local-indexed smoothing width.
- `paper/sections/05b_cls_stages.tex:137`: `H_{\varepsilon_i}` is used in the numerator.
- `paper/sections/05b_cls_stages.tex:138`: `H'_{\varepsilon_i}` is used in the denominator.
- `paper/sections/10d_ridge_eikonal_nonuniform.tex:120`: "`\\varepsilon_\\text{local}(\\bm{x})`"
- `src/twophase/levelset/reinit_eikonal.py:144`: "`H'_ε(φ) = ψ(1-ψ)/ε(i,j)`"
- `src/twophase/levelset/ridge_eikonal_reinitializer.py:109`: "`w = psi_new * (1.0 - psi_new) / self._eps_local`"

Original issue: §5.2 presented Stage F as the mass closure after "Ridge--Eikonal / xi-SDF / FMM" reinitialization, but the equation used scalar `H_epsilon` and `H'_epsilon`. The nonuniform/FMM path explicitly replaces the width by `epsilon_local(x)` in §10 D4, and both implementation paths use local `eps_arr` / `self._eps_local` in the derivative. A reader implementing the original §5.2 literally would have used the wrong denominator and reconstruction on nonuniform grids.

Resolution: fixed in `paper/sections/05b_cls_stages.tex` by using `H_{\varepsilon_i}` and `H'_{\varepsilon_i}` in Stage F, with `\varepsilon_i=\varepsilon` for the uniform xi-SDF specialization and `\varepsilon_i=\varepsilon_\text{local}(\bm{x}_i)` for the nonuniform Ridge--Eikonal/FMM path. The matching §5.1 Eikonal mass-correction notation was also updated to `H_{\varepsilon(\bm{x})}`.

## Confirmed Resolved

- FATAL zero-crossing preservation vs mandatory phi-space mass correction: resolved by scoping the invariant to the pre-correction field and tracking `delta_phi`.
- FATAL psi-curvature contradiction: resolved by replacing the broad ban with the monotone-invariant psi-direct curvature path and a narrower warning against naive/unnormalized psi curvature.
- MAJOR exact mass-closure wording: resolved by describing psi/phi corrections as linearized/Newton updates with residual monitoring.
- MAJOR Godunov/WENO-HJ fallback CFL: resolved by separating HJ CFL from legacy compression--diffusion parabolic CFL.
- MAJOR validation reference overclaim: resolved by downgrading parameter sweeps to explicit experiment settings / future sensitivity validation and routing iteration-count support to U4.
- MINOR stale A3 paths/comments: resolved.
