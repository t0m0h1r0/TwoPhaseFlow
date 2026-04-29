# CHK-RA-APPEND-002 — Appendix Rereview

Date: 2026-04-29
Worktree: `.claude/worktrees/ra-appendix-review-retry-20260429`
Branch: `ra-appendix-review-retry-20260429`
id_prefix: `RA-APPEND`
Reviewer stance: second-pass strict reviewer after CHK-RA-APPEND-001 fixes.

## Verdict

Post-fix verdict: acceptable after minor-to-major residual cleanup in this branch.

The first review removed the main stale LGMRES / `PPESolverSweep` claims, but the rereview found two residual issues that could still confuse reviewers about the implemented algorithm and the strength of appendix evidence. Both were fixed.

## Findings and Fixes

| ID | Severity | Finding | Fix |
|---|---:|---|---|
| R-1 | Major | `appendix_ppe_pseudotime.tex` still said "本稿では実装の簡便さからスウィープ型を採用する", contradicting the corrected `PPESolverDefectCorrection` standard-contract text. | Reframed sweep text as a conditional preconditioner/theory path and removed production-adoption wording. |
| R-2 | Major | The pseudo-time and DC iteration notes still named Krylov/GMRES/CG as a direct PPE route, which reads like an endorsed solver family despite PPE policy. | Replaced with "explicit matrix direct solve" language and kept the point limited to splitting-error comparison. |
| R-3 | Major | `appendix_bootstrap.tex` claimed one reinitialization cycle yields an unconditional SDF order and that HFE `O(h^6)` total accuracy is achieved "on average." This overstates the evidence. | Rewrote as a conditional consistency step; HFE design accuracy is not claimed from bootstrap initialization alone. |

## Residual Risk

- Appendix D still preserves pseudo-time and sweep analysis as background. This is acceptable because it is now explicitly conditional and separated from the standard implementation contract.
- No numerical algorithm or implementation code was changed. [SOLID-X] Paper/docs-only; no production class/module boundary change.

## Verification

- Stale appendix solver audit: no hits for `LGMRES`, `PPESolverSweep`, `ppe_solver_type="sweep"`, `Krylov`, `GMRES`, `CG 法`, or "本稿では実装の簡便さ".
- Overclaim audit: no hits for "時間平均的に達成" or "無条件に保証".
- `git diff --check`: OK.
- `cd paper && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: OK; `paper/main.pdf` generated, 234 pages.
- Final log diagnostic grep for LaTeX warnings, overfull/underfull boxes, missing characters, undefined controls, emergency/fatal errors: 0 hits.
