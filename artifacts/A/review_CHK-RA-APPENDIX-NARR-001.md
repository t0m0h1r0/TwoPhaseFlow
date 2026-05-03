# CHK-RA-APPENDIX-NARR-001 — Appendix Narrative / Notation Review

Date: 2026-05-03
Branch: `ra-appendix-narrative-review-20260503`
Worktree: `.claude/worktrees/ra-appendix-narrative-review-20260503`

## Verdict

PASS after major correction.  The appendix no longer presents an obsolete pressure-stabilization branch as if it were part of the thesis route.  The supplemental material now supports the main narrative: CCD/FCCD for high-order evaluation, pressure-jump / phase-separated PPE for high-density and low-Weber closure, IMEX--BDF2 time integration, HFE for jump-aware Hermite extension, and DC-PPE as an operator contract rather than a one-off implementation trick.

## Strict Review Findings and Fixes

1. **Obsolete pressure branch removed at the root.**
   Appendix E still contained Rhie--Chow / C-RC derivations and labels after the main paper had moved to pressure-jump, FCCD, HFE, and phase-separated PPE.  These sections were removed rather than renamed.  The remaining FVM face-coefficient material is explicitly framed as a low-order reference and consistency check, not the thesis closure.

2. **Predictor appendix replaced with the current time-integration story.**
   The former ADI / Crank--Nicolson predictor supplement contradicted the current IMEX--BDF2 and implicit-BDF2 full-stress Helmholtz DC route.  It was replaced by `appD_predictor_imex_bdf2.tex`, which explains the predictor, residual acceleration, full-stress Helmholtz DC, and HFE in the same contract used by the main text.

3. **DC-PPE appendix generalized from an implementation recipe to an operator contract.**
   The old derivation assumed an RC/DCCD-filtered divergence and a one-field CCD product-rule PPE as the universal path.  The revised appendix defines the target operator and right-hand side as path dependent, with one-field product-rule CCD as a component-verification route and phase-separated PPE plus pressure-jump rows as the thesis route.

4. **Pseudo-time PPE appendix aligned with the same pressure contract.**
   The pseudo-time discussion now starts from `PPESolverDefectCorrection` and a path-dependent target operator.  ADI is described only as a comparison/preconditioner model, avoiding a false standard-path claim.

5. **Notation and narrative drift removed.**
   Stale implementation words and code-file references were removed from the paper appendix; terminology was harmonized around smoothed-Heaviside, signed-distance field, six-stage bootstrap, pressure-jump closure, and fixed-grid comparison mode.  Appendix float placement was normalized to `[htbp]`.

6. **Known build warnings fixed.**
   The remaining `09f_pressure_summary` underfull box and Chapter 12 float-only-page warning were corrected by table column ragged-right wrapping and standard float placement.

## Validation

- `git diff --check` PASS.
- `make -C paper` PASS; `paper/main.pdf` rebuilt at 242 pages.
- Final `paper/main.log` scan PASS for `Underfull \hbox`, `Overfull \hbox`, `Text page`, and `LaTeX Warning`.
- Stale-term scan PASS for Rhie--Chow / C-RC, removed ADI appendix name, stale implementation terms, `.py` / `yaml` references in appendices, `smoothed Heaviside`, and `Level Set`.
- Appendix float scan PASS for `[ht]` / `[!ht]`.

## SOLID-X

No violation.  This CHK changes paper and review/audit documentation only.  No production solver boundary changed, no tested code was deleted, and no FD/WENO/PPE fallback or parameter workaround was introduced.
