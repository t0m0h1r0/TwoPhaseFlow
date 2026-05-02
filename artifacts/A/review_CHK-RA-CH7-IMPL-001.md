# CHK-RA-CH7-IMPL-001 — Chapter 7 Implementation Audit

Date: 2026-05-02
Branch: `ra-ch7-implementation-audit-20260502`
Verdict: PASS AFTER FIX

## Scope

- Paper: `paper/sections/07_time_integration.tex`
- Library: `src/twophase/simulation/`, `src/twophase/ppe/fccd_matrixfree.py`, `src/twophase/ns_terms/viscous.py`, `src/twophase/levelset/fccd_advection.py`
- Focus: CLS TVD-RK3 order, NS IMEX-BDF2/EXT2, implicit-BDF2 viscous DC, PPE pressure-jump CSF, IPC projection width, timestep synthesis, non-uniform grid support, GPU path.

## Findings

- CLS update already follows the Chapter 7 causal order: projected `u^n` advects `psi` before material fields, curvature, PPE, and buoyancy are assembled.
- IMEX-BDF2 implementation already uses EXT2 convection only when projected velocity/convection history is ready, uses BDF1 startup otherwise, and applies `dt_proj = 2/3 dt` to the PPE/corrector.
- Viscous DC already evaluates the high-order residual with `ViscousTerm._evaluate`, and the low-order Helmholtz correction shares `mu`, `rho`, topology, and physical non-uniform spacings.
- Divergence found: public/default construction and omitted YAML time-integrators still selected legacy AB2 / forward-Euler or CN / CSF / FVM paths, so an unspecified library run did not instantiate the Chapter 7 production stack.
- Divergence found: GPU request could silently fall back to CPU when CuPy/CUDA was unavailable, violating the no-fallback policy for GPU validation.

## Fixes

- Default NS stack now selects `imex_bdf2` convection, `implicit_bdf2` viscous predictor, `pressure_jump` surface tension, FCCD PPE, phase-separated coefficients, affine jump coupling, FCCD pressure gradient, and no body-force surface-tension gradient.
- Non-uniform default construction now uses `ridge_eikonal`, avoiding the Chapter 5 uniform-basis `eikonal_xi` path on refined grids.
- Explicit legacy paths remain available, but tests that assert legacy FVM/WENO/CSF behavior now specify those schemes explicitly.
- `Backend(use_gpu=True)` / `TWOPHASE_USE_GPU=1` now fails closed when CUDA is unavailable instead of silently switching to NumPy.

## A3 Traceability

- Equation: Chapter 7 `eq:predictor_imex_bdf2`, `eq:helmholtz_implicit_bdf2`, `eq:viscous_bdf2_dc`, `eq:ppe_jump_decomposed`, and IPC `dt_proj`.
- Discretization: FCCD flux divergence for CLS/PPE, UCCD6/FCCD convection, high-order full-stress viscous residual, low-order variable-coefficient Helmholtz correction, affine Young--Laplace pressure-jump face gradient.
- Code: `TwoPhaseNSSolver` defaults and config builders route into `compute_ns_predictor_stage`, `ImplicitBDF2ViscousPredictor`, `ViscousHelmholtzDCSolver`, `PPESolverFCCDMatrixFree`, and `FCCDDivergenceOperator`.

## GPU / Non-Uniform Check

- GPU default stack construction remains on CuPy arrays and instantiates `PPESolverFCCDMatrixFree` + `ImplicitBDF2ViscousPredictor`.
- FCCD GPU primitive smoke passes on the remote CUDA host.
- Non-uniform constructor and timestep-budget smoke pass with the default `ridge_eikonal` path.

## Validation

- `git diff --check` PASS.
- Remote targeted CPU/GPU pytest PASS:
  - `test_construction_uniform`
  - `test_step_uniform_no_nan`
  - `test_construction_nonuniform`
  - `test_dt_max_nonuniform`
  - `test_dt_max_crank_nicolson_omits_viscous_stability_limit`
  - `test_pipeline_can_solve_fccd_ppe_smoke`
  - `test_fccd_not_constructed_when_unused`
  - `test_pipeline_uses_matrixfree_fvm_ppe`
  - `test_pipeline_can_select_direct_fvm_ppe`
  - `test_surface_tension_uses_configured_gradient_operator`
  - `test_weno5_advection_constructed_from_scheme`
  - `--gpu test_fccd_face_gradient_gpu_matches_cpu`
  - `--gpu test_ch7_default_ns_stack_constructs_on_gpu`
- Broad `make test` was accidentally invoked with node arguments that remote pytest treated as full-suite collection; failures included pre-existing missing experiment YAML files and unrelated stability checks. Targeted changed-path validations above pass.

## SOLID-X

- No tested code was deleted.
- Legacy alternatives remain explicit strategies instead of hidden fallbacks.
- Paper-exact default routing is centralized in construction/config normalization rather than duplicated in timestep logic.
