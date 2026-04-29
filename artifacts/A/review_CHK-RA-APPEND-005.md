# CHK-RA-APPEND-005 — Appendix post-merge strict review

Date: 2026-04-29
Branch/worktree: `ra-appendix-review-retry-20260429` / `.claude/worktrees/ra-appendix-review-retry-20260429`
Scope: appendices A--G after CHK-RA-APPEND-004 main merge
Verdict: Pass after targeted fixes. The appendix architecture A--G is acceptable, but source-level numbering comments and one stability claim were still too loose for reviewer-facing maintenance.

## Reviewer findings

### A-1 Major — Appendix letters in source comments were stale after A--G consolidation

- Several appendix subfiles still carried pre-consolidation comments such as appendix B/C/D/F/H or old internal numbering.
- Although mostly hidden from PDF output, these comments are part of the editorial source of truth and would mislead future reviewers/editors when tracing appendix sections.

Action:
- Aligned `paper/main.tex` and appendix source comments to the current A--G hierarchy.
- Updated interface, CCD, advection, pressure, bootstrap, and verification appendix comments.
- Removed unnecessary historic letter references where they no longer clarified provenance.

### A-2 Major — Appendix B/E substructure comments did not match the compiled structure

- Appendix B was described as B.1--B.5 while the compiled structure is B.1--B.4 after `appendix_interface_s3` was consolidated.
- Appendix E comments summarized only E.1--E.3, but the compiled appendix also contains E.4 C/RC Taylor proof and E.5 pressure-step implementation details.

Action:
- Corrected Appendix B to B.1--B.4.
- Corrected Appendix E summary to E.1--E.5 and aligned implementation detail comments to E.5.1/E.5.2.

### A-3 Medium — Pseudo-time PPE stability wording overclaimed beyond the model

- The appendix used phrases equivalent to "unconditional stability" and implied that large `\Delta\tau` could be chosen freely.
- The surrounding derivation is an idealized linear/splitting model, not a blanket implementation guarantee under variable coefficients, splitting residual floors, or high density ratios.

Action:
- Reworded the claim as A-stability / non-amplification for the linear positive-definite model.
- Added explicit caveats for splitting error floors, conditioning, coefficient nonuniformity, and residual stagnation.

### A-4 Confirmed — No need to resurrect former Appendix N

- The HFE convergence appendix remains correctly removed.
- HFE convergence evidence is still centralized in main-body U6-c.
- No residual references to `appendix_hfe_verify`, `hfe_convergence`, `Appendix N`, or `付録N` were found in the active appendix sources.

## Validation

- `git diff --check`: pass.
- `cd paper && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: pass.
- `paper/main.pdf`: regenerated, 226 pages.
- Stale appendix/solver overclaim grep: no residual hits for obsolete H--N appendix references, old HFE appendix artifacts, `LGMRES`, `PPESolverSweep`, `ppe_solver_type=`, `Krylov`, `無条件安定`, or "任意に大き".

## SOLID audit

[SOLID-X] Paper/source-comment and LaTeX prose review only. No `src/twophase/` code, production class boundary, module boundary, solver interface, or experiment implementation was changed.

## Commits

- `92df967 paper: tighten appendix postmerge review`
