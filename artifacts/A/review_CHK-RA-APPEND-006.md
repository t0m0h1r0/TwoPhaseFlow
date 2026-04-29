# CHK-RA-APPEND-006 — Appendix re-review on reference-claim boundaries

Date: 2026-04-29
Branch/worktree: `ra-appendix-review-retry-20260429` / `.claude/worktrees/ra-appendix-review-retry-20260429`
Scope: appendices B, E and pressure-step implementation notes
Verdict: Pass after fixes. The appendix structure remains acceptable, but several reference derivations still read like production guarantees.

## Reviewer findings

### A-1 Major — Viscosity arithmetic mean was overstated as an exact CLS consequence

- Appendix B claimed that the CLS equilibrium profile makes `\psi` linear under the Eikonal condition and therefore yields an exact arithmetic face average for viscosity.
- This is mathematically too strong: `H_\varepsilon(\phi)` is generally nonlinear even when `\phi` is a signed-distance function.

Action:
- Reframed the derivation as a linear-reconstruction / trapezoidal-rule FVM approximation.
- Stated that exactness holds only in the local linear limit.
- Clarified that the production viscous term uses CCD product-rule differentiation, and interface-band order must be judged by verification.

### A-2 Major — FVM/Rhie--Chow reference material read as the current production path

- Appendix E mixed reference FVM/RC derivations with phrases such as "本研究では" and "必須", making Rhie--Chow appear mandatory in the current standard stack.
- This conflicted with the surrounding statement that DCCD/FCCD + HFE replaces the Rhie--Chow path.

Action:
- Renamed "完全な定式化" sections to "参照定式化".
- Reworded Rhie--Chow equations as conditional on using the RC path.
- Made PPE RHS RC divergence and surface-tension RC extension conditions explicitly conditional.

### A-3 Medium — Pseudo-time/LTS guidance still sounded like a blanket guarantee

- Tolerance recommendations used "十分".
- Local time stepping said density dependence is completely canceled and dynamic `C_\tau` increases dramatically accelerate convergence.

Action:
- Changed fixed tolerances to starting points confirmed by outer residual and physical observable convergence.
- Limited LTS cancellation to an idealized local linear model.
- Replaced dramatic acceleration wording with a conditional practical benefit.

### A-4 Minor — Numerical direct solve wording used "exact" too freely

- Direct LU solve wording implied mathematical exactness.

Action:
- Reworded to numerical linear algebra tolerance.
- Limited `O(h^6)` DC output wording to smooth-RHS verification conditions.

## Validation

- `git diff --check`: pass.
- `cd paper && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: pass.
- Final `main.log` diagnostic count for warnings/errors/overfull/underfull/missing characters: 0.
- `paper/main.pdf`: regenerated, 227 pages.
- Stale/overclaim grep: no hits for the reviewed high-risk patterns (`厳密な導出`, `完全な定式化`, unconditional stability wording, obsolete Appendix N/HFE artifacts, old PPE solver names).

## SOLID audit

[SOLID-X] Paper prose and appendix review only. No `src/twophase/` code, production class boundary, module boundary, solver interface, or experiment implementation was changed.

## Commits

- `5df47b8 paper: qualify appendix reference claims`
