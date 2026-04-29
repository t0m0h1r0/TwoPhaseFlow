# CHK-RA-APPEND-001 — Appendix Strict Reviewer Audit

Date: 2026-04-29
Worktree: `.claude/worktrees/ra-appendix-review-retry-20260429`
Branch: `ra-appendix-review-retry-20260429`
id_prefix: `RA-APPEND`
Reviewer stance: journal reviewer, appendix-only, strict consistency check.

## Scope

- Appendix material included after `\appendix` in `paper/main.tex`.
- Primary files reviewed: `appendix_nondim_details`, `appendix_interface*`, `appendix_ccd*`, `appendix_advection`, `appendix_pressure*`, `appD_*`, `appendix_bootstrap`, and `appendix_verification_details`.
- Cross-check axis: paper claims vs. project PPE policy, current `src/twophase/ppe/*` implementation names, and LaTeX build health.

## Verdict

Pre-fix verdict: major revision required.

The appendix contained stale PPE implementation claims that would mislead a reviewer about the actual solver family. The critical issues were corrected in this branch. Post-fix build is clean.

## Findings and Disposition

| ID | Severity | Finding | Disposition |
|---|---:|---|---|
| C-1 | Critical | Appendix CCD-Poisson solver text presented LGMRES as the adopted PPE solver, contradicting PR-6 and current `PPESolverCCDLU` direct-solve implementation. | Fixed: rewritten as direct LU reference solve, limited to smooth-RHS component verification/debugging. |
| C-2 | Critical | Appendix pseudo-time section claimed `PPESolverSweep` / `ppe_solver_type="sweep"` was the implemented standard path, but current implementation uses `PPESolverDefectCorrection` with explicit base solver/operator contracts. | Fixed: standard path now names `PPESolverDefectCorrection`; sweep theory is framed as preconditioner/design background. |
| C-3 | Major | High-density DC theory recommended GMRES + FD preconditioning, conflicting with the paper's split-PPE + HFE strategy and PPE solver policy. | Fixed: high-density guidance now points to split PPE + HFE or stable FVM direct base solves. |
| M-1 | Major | Predictor ADI appendix described HFE for pressure extension as a future split-PPE extension, while split PPE is already a principal strategy in §9. | Fixed: wording changed to "split PPE path"; smoothed-Heaviside monolithic path remains explicitly excluded. |
| m-1 | Minor | Several appendix file comments still preserve old appendix-letter group names. They are non-rendered and do not affect PDF correctness. | Deferred: safe to clean in a later editorial-only pass. |

## Residual Reviewer Notes

- The appendix still contains historical pseudo-time and sweep analysis. This is acceptable only because the standard implementation text now explicitly separates theory/background from production solver contracts.
- No `src/twophase/` behavior was changed. [SOLID-X] Paper/docs-only review; no class/module boundary change.

## Verification

- `rg` audit: no appendix occurrences of `LGMRES`, `PPESolverSweep`, `ppe_solver_type="sweep"`, `Krylov 実装`, or `GMRES + FD` remain.
- `git diff --check`: OK.
- `cd paper && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: OK; `paper/main.pdf` generated, 234 pages.
- Final log diagnostic grep for LaTeX warnings, overfull/underfull boxes, missing characters, undefined controls, emergency/fatal errors: 0 hits.
