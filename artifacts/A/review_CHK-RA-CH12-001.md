# Review CHK-RA-CH12-001

Date: 2026-05-03
Scope: `experiment/ch12/*`, `paper/sections/12*.tex`, `paper/figures/ch12_*.pdf`, with consistency checked against the latest Chapters 4--11 contracts.

## Verdict

PASS after experiment refresh. Open FATAL: 0. Open MAJOR: 0. Open MINOR: 0.

## Reviewer Findings And Fixes

### MAJOR-1: U2-b used the retired production interpretation

Finding: U2-b still described the production pressure path as CCD-LU with a Dirichlet patch. That contradicts the current Chapter 8--11 contract: CCD/Kronecker Poisson remains a smooth/reference component, while the production PPE baseline is the `PPEBuilder` FVM/spsolve path with Neumann wall treatment and a gauge constraint.

Fix: `experiment/ch12/exp_U2_ccd_poisson_ppe_bc.py:136` now drives `PPEBuilder` directly, solves the FVM sparse system, aligns the pinned gauge with the exact pressure, and reports the current FVM PPE slope. `paper/sections/12u2_ccd_poisson_ppe_bc.tex:16` and `paper/sections/12_component_verification.tex:112` were updated to state the corrected contract and refreshed slope $2.00$.

### MAJOR-2: U8 used a stale CN/explicit-cross time contract

Finding: U8 still tested Crank--Nicolson and an explicit cross-term layer model, producing a first-order Layer B/C limitation. That no longer matches the latest Chapter 7/11 route: TVD--RK3 for CLS, EXT2/IMEX-style second-order extrapolation for predictor terms, and implicit-BDF2 plus full-stress defect-correction for viscosity.

Fix: `experiment/ch12/exp_U8_time_integration_suite.py:70` now measures EXT2/AB2, `experiment/ch12/exp_U8_time_integration_suite.py:101` measures BDF1-started implicit-BDF2 diffusion and stability, and `experiment/ch12/exp_U8_time_integration_suite.py:211` measures a full variable-viscosity operator without explicit cross-lag. `paper/sections/12u8_time_integration.tex:5` and summary tables were refreshed: U8-a/b/c slopes are $3.04/2.05/2.01$ and U8-d is $2.00$--$2.03$ over Layer A/B/C cases.

## Sufficiency Review

- U1, U3--U5, U7, and U9 remain necessary and sufficient component tests for the Chapter 4--11 equation/discretization/code chain.
- U6 remains a valid negative lumped-PPE component test plus HFE component check; the positive phase-separated pressure-jump path is an integrated Chapter 13 validation, not a missing Chapter 12 primitive.
- U3 covers nonuniform/FCCD/Ridge--Eikonal primitive metrics; every-step interface-following rebuild is a coupled Chapter 13/14 runtime concern rather than a new standalone Chapter 12 experiment.
- U4 remains sufficient as an explicit Godunov/DGR component comparison; production Ridge--Eikonal single-shot usage is covered by the current Chapter 10--11 narrative and downstream validation.

## Final Checks

- Remote-first experiment refresh: `make cycle EXP=experiment/ch12/exp_U2_ccd_poisson_ppe_bc.py` PASS; targeted post-push `make run` PASS with U2-b FVM slope $2.00$.
- Remote-first experiment refresh: `make cycle EXP=experiment/ch12/exp_U8_time_integration_suite.py` PASS; targeted post-push `make run` PASS with U8-d full-operator BDF2 slopes $2.00$--$2.03$.
- Chapter sweep: `make run-all CH=ch12` PASS for unchanged U1/U3--U7/U9; U2/U8 were subsequently corrected by push + targeted reruns after the stale remote copy was noticed.
- Paper build: `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` PASS; no fatal undefined/citation/multiply-defined errors found.
- Static checks: `git diff --check` PASS; targeted `py_compile` for U2/U8 PASS.
- SOLID audit: [SOLID-X] experiments/paper/figures only; no production boundary changed, no tested code deleted, no FD/WENO/PPE fallback introduced, and PR-4 experiment toolkit/plot-only workflow remains intact.
