# CHK-RA-DC-ADOPT-001 — DC solver adoption review

Verdict: CONDITIONAL ADOPT. The supplied memo is correct on the central
mathematics, but it should not be adopted as a blanket solver replacement.

## Scope

- Branch: `ra-dc-adoption-review-20260502-r2`
- id_prefix: `RA-DC-ADOPT`
- Classification: FULL-PIPELINE, theory and architecture decision
- Local evidence inspected: `paper/sections/07_time_integration.tex`,
  `paper/sections/09_ccd_poisson.tex`,
  `paper/sections/09d_defect_correction.tex`,
  `paper/sections/09f_pressure_summary.tex`,
  `paper/sections/11_full_algorithm.tex`,
  `src/twophase/simulation/viscous_predictors.py`,
  `experiment/ch14/config/README.md`,
  `docs/memo/CHK-RA-VISCOUS-DC-001_viscous_bdf2_dc.md`, and
  `docs/memo/CHK-RA-VISCOUS-DC-003_hypothesis_validation.md`.

## Decision

1. Chapter 7 viscous Helmholtz DC: adopt the mathematical caution, but keep the
   current implementation contract.
   The correct fixed point is the high-order full-stress system
   `A_H u = b`, with the low-order Helmholtz `A_L` acting only as a correction
   inverse. The paper and current implementation already follow this contract:
   high residual evaluation is by `A_H`, the low operator shares `mu`, `rho`,
   boundary topology, and interface-band structure, and GMRES remains available
   as an explicit YAML-selected comparison path.

2. Do not adopt automatic GMRES/FGMRES fallback for viscous production runs now.
   The memo's FGMRES recommendation is mathematically reasonable for measured
   stagnation, but it conflicts with the current recorded design choice
   ("GMRES is explicit selection, not fallback") and is not backed here by a
   new failure case, trigger threshold, or regression target. Adding automatic
   fallback would change reproducibility: two runs with identical YAML could
   take different linear-solver paths depending on residual history. The
   adopted near-term policy is therefore: DC remains the default production
   path; GMRES remains explicit; FGMRES + `A_L` preconditioning is a future
   candidate only after a concrete stagnation benchmark is recorded.

3. Chapter 9 PPE DC: adopt for phase-separated PPE + HFE + phase-internal
   constant-density Poisson.
   When the PPE is split by phase, the high/low operator mismatch is small
   inside each smooth phase, the pressure jump is carried by HFE/interface
   data, and `DC k=3` with high-residual monitoring is consistent with the
   current Chapter 9 story. This is the intended production mathematics.

4. Do not adopt fixed-count DC as a primary solver for high-density-ratio
   smoothed-Heaviside one-field PPE.
   Excluding appendix-based spectral arguments weakens a hard "no", but it
   does not remove the body-text concern: interface-crossing variable
   coefficients create a discretization error and conditioning problem that
   fixed Richardson/DC iterations do not cure. Current text already treats the
   one-field path as low/mid-density comparison or diagnostic, not the
   high-density pressure-jump closure.

5. Do not route PPE to GMRES/FGMRES under this decision.
   `docs/03_PROJECT_RULES.md` currently states PR-6: PPE uses DC k=3 plus a
   low-order direct solve and forbids LGMRES for PPE. The supplied memo's
   "GMRES as safer fallback" is useful theory context, but changing the PPE
   solver policy would require a separate explicit exception and validation
   campaign.

## Mathematical audit

- DC is preconditioned Richardson:
  `x_{m+1}=x_m+omega A_L^{-1}(b-A_H x_m)`, with error propagator
  `I-omega A_L^{-1}A_H`.
- Accuracy is not inherited from `A_L`; it is inherited from solving the
  high-order residual `b-A_H x` or `b-L_H p` to the required tolerance.
- Fixed iteration count is evidence-based, not a proof obligation. `k=3` is
  acceptable where the phase-separated PPE verification applies; it is not a
  universal contract for one-field variable-density PPE.
- The low viscous operator must remain Helmholtz-like and share coefficients,
  boundary constraints, and interface-band topology. A constant-coefficient
  Poisson surrogate is rejected for viscosity.
- Poisson gauge/nullspace handling remains part of the PPE contract and is not
  solved by DC itself.

## Consequences

- No production code change is made in this review.
- No paper rewrite is required: Chapters 7, 9, and 11 already encode the main
  adopted distinctions.
- The supplied memo should be treated as a policy reinforcement:
  high residuals must remain visible, fixed-count DC must not be overclaimed,
  and one-field PPE stagnation should trigger path selection toward the
  phase-separated pressure-jump closure rather than blind iteration increases.

## Future trigger for revisiting FGMRES

Reopen the viscous solver policy only if a benchmark records at least one of:

- high residual stagnation for viscous DC under large `tau`;
- high `mu/rho` jump or interface-band switching causing nonmonotone residuals;
- a reproducible case where explicit `solver.kind: gmres` succeeds and DC does
  not under the same `A_H` residual tolerance;
- a validated `A_L` preconditioner API that keeps YAML-selected solver paths
  reproducible.

## SOLID audit

- [SOLID-X] Review and architecture decision only; no production code boundary
  changed and no tested implementation deleted.
