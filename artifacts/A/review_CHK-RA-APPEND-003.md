# CHK-RA-APPEND-003 — Appendix third strict rereview

Date: 2026-04-29
Branch/worktree: `ra-appendix-review-retry-20260429` / `.claude/worktrees/ra-appendix-review-retry-20260429`
Scope: appendix PPE / defect-correction / pseudo-time solver narrative
Verdict: PASS after fixes

## Reviewer stance

The appendix was reviewed as a strict referee report, focusing on whether solver claims are supported by the implementation contract and by the cited verification range. The key criterion was to reject any wording that reads as an unconditional all-density-ratio convergence or accuracy guarantee.

## Findings and fixes

### T-1 Major — split PPE density-ratio wording overclaimed scope

- Location: `paper/sections/appD_dc_ppe_iteration.tex`
- Issue: the note stated that split PPE with `k=3` achieves `O(h^7)` / `O(h^5)` for all density ratios. This could be read as a guarantee for the one-shot smoothed-Heaviside PPE path.
- Fix: limited the claim to the verified split-PPE setting, explained why constant-density subdomains avoid direct density-ratio degradation, and explicitly stated that this is not an all-density-ratio guarantee for the one-shot smoothed-Heaviside PPE.

### T-2 Major — pseudo-time defect correction promised full CCD accuracy

- Location: `paper/sections/appendix_ppe_pseudotime.tex`
- Issue: “complete CCD spatial accuracy” and “accuracy is not lost” made the FD-left / CCD-residual configuration sound unconditionally accurate.
- Fix: replaced the guarantee with a target-residual contract: accuracy is judged by the target operator and outer residual, while tolerance, base solver error, boundary/interface coefficient treatment, and residual floors remain limiting factors.

### T-3 Major — method table encoded a production guarantee

- Location: `paper/sections/appendix_ppe_pseudotime.tex`
- Issue: the “FD left + CCD residual [standard] = O(h^6), no splitting error” row conflated one theoretical configuration with the implementation contract.
- Fix: changed the row to `base + target residual [standard contract]`, made spatial order target-operator dependent and splitting-error behavior base-dependent, and moved FD+CCD into a footnoted configuration.

### T-4 Major — spectral appendix overstated convergence theory

- Location: `paper/sections/appendix_numerics_solver_s5.tex`
- Issue: the text said the spectral analysis “theoretically guarantees” convergence and that `k=3` reaches `O(h^6)` without sufficiently restricting the conditions.
- Fix: reframed the analysis as an idealized interpretation criterion and restricted `k=3` / `O(h^6)` to equal-density smooth-RHS verification, with an explicit warning not to extrapolate to variable-density interface problems.

## Validation

- Stale solver / overclaim audit: 0 hits for `LGMRES`, `PPESolverSweep`, `ppe_solver_type="sweep"`, stale Krylov/GMRES/CG PPE route wording, unconditional CCD guarantee wording, and all-density-ratio achievement wording.
- `git diff --check`: pass.
- `cd paper && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: pass.
- Final log diagnostic count for warnings/errors/overfull/underfull/missing characters: 0.
- `paper/main.pdf`: regenerated, 234 pages.

## SOLID audit

[SOLID-X] Paper/docs-only review and wording correction. No `src/twophase/` code, production class boundary, module boundary, or solver interface was changed.

## Commit

- `a11a35b paper: soften appendix convergence claims`

## Residual risk

The appendix still contains idealized solver analysis. It is now explicitly marked as conditional support for interpreting verification results, not as a universal production guarantee. Further tightening should be driven by new numerical evidence, not by prose inference.
