# CHK-RA-CH11-IMPL-001 — Chapter 11 Implementation Audit

Date: 2026-05-02
Branch: `ra-ch11-implementation-audit-20260502`
Verdict: PASS AFTER FIX

## Scope

- Paper: `paper/sections/11_full_algorithm.tex`, with Chapter 5 reinitialization constraints and Chapter 13/15 validation-boundary notes.
- Library: `src/twophase/levelset/`, `src/twophase/simulation/`, `src/twophase/ppe/`, `src/twophase/coupling/`.
- Focus: seven-stage algorithm, adaptive reinitialization, DGR applicability, material/curvature ordering, IMEX-BDF2 predictor, IPC pressure increment, FCCD/affine pressure-jump projection, non-uniform-grid support, GPU residency.

## Findings

- Divergence fixed: `PsiDirectTransport` only supported fixed-cadence reinitialization, while Chapter 11 Step 2 requires the volume-monitor trigger `M/M_ref > theta_reinit`.
- Divergence fixed: the modern NS pipeline solved and returned the PPE unknown as a total pressure/warm-start field, while Chapter 11 Steps 5--7 require IPC: predictor uses `-rho^-1 grad(p^n)`, PPE solves `delta p`, corrector uses `delta p`, and stored pressure is `p^n + delta p`.
- Confirmed: Stage ordering already follows Chapter 11: interface transport, material fields from `psi^{n+1}`, direct-psi curvature, predictor, PPE, corrector.
- Confirmed: fixed-grid FCCD/affine pressure-jump paths reuse the same interface face data in PPE and correction; no CPU fallback was added.
- Boundary: DGR is implemented as an exact operator, but automatic every-20-step DGR is not forced in the default ridge-eikonal path because Chapter 5 forbids DGR for narrow slots and sigma>0 fold-prone oscillatory cases; applying it blindly would violate the paper caveats.
- Boundary: full long-time/non-uniform pressure-jump + HFE statistics remain a validation gate in Chapter 13; this audit does not mask that boundary with a fallback.

## Fixes

- Added adaptive reinitialization trigger fields through config, runtime options, solver binding, and `PsiDirectTransport`.
- Preserved explicit fixed schedules by treating existing `every_steps` YAML as `mode: fixed`; default construction now uses adaptive mode with threshold `1.10`.
- Implemented IPC pressure history in `TwoPhaseNSSolver`: previous total pressure is fed to the predictor, PPE starts `delta p` from zero, base pressure is accumulated separately, and the returned pressure is the physical total pressure.
- Added CPU tests for adaptive reinit, config parsing, IPC predictor pressure gradient, IPC pressure accumulation, and projection time-width consistency.
- Added GPU smoke tests for adaptive reinit and IPC pressure accumulation staying on CuPy arrays.

## A3 Traceability

- Equation: Chapter 11 Step 2 `M/M_ref > theta_reinit`, Step 5 `-rho^{-1} G_Gamma p^n`, Step 6 `L(delta p)=D u*/dt`, Step 7 `p^{n+1}=p^n+delta p`.
- Discretization: `grid.cell_volumes()` weighted volume monitor; backend-native FCCD/CCD pressure gradient; PPE unknown reset to zero for increment solve; face-flux projection continues to use shared affine jump context.
- Code: `PsiDirectTransport`, `TwoPhaseNSSolver._prepare_step_inputs`, `compute_ns_predictor_stage`, `solve_ns_pressure_stage`, `correct_ns_velocity_stage`.

## GPU / Non-Uniform Check

- Adaptive monitor uses backend arrays and non-uniform control volumes; only the scalar trigger decision synchronizes to host, which is unavoidable for Python control flow.
- IPC pressure accumulation keeps device arrays on GPU; host pressure mirror remains disabled for GPU state history.
- Non-uniform projection consistency remains tied to the FCCD/FVM face operator path; no CCD-only non-uniform fallback was introduced.

## Validation

- `git diff --check` PASS.
- Local targeted pytest PASS:
  - `test_psi_direct_transport_adaptive_reinitializes_on_volume_monitor`
  - `test_psi_direct_transport_reinitializes_after_initial_step_only`
  - `test_reinitialization_adaptive_schedule_parses_threshold`
  - `test_construction_uniform`
  - `test_predictor_includes_ipc_previous_pressure_gradient`
  - `test_pressure_projection_uses_projection_dt`
  - `test_pressure_stage_accumulates_ipc_pressure_increment`
  - `test_imex_bdf2_predictor_uses_ext2_and_projection_dt`
  - `test_affine_jump_corrector_forwards_interface_context`
  - `test_pipeline_can_solve_fccd_ppe_smoke`
- Remote targeted pytest PASS:
  - `test_predictor_includes_ipc_previous_pressure_gradient`
  - `test_pressure_stage_accumulates_ipc_pressure_increment`
  - `test_psi_direct_transport_adaptive_reinitializes_on_volume_monitor`
  - `test_reinitialization_adaptive_schedule_parses_threshold`
  - `--gpu test_psi_direct_adaptive_reinit_keeps_gpu_device`
  - `--gpu test_ch7_default_ns_stack_constructs_on_gpu`
  - `--gpu test_ipc_pressure_increment_keeps_gpu_device`
- Known out-of-scope existing failure observed: `test_phase_separated_pressure_jump_stack_one_step_no_nan` still trips the pre-existing `ppe_rhs_phase_mean_after_max < 1e-10` diagnostic tolerance (`3.898e-05`), matching the prior phase-mean diagnostic issue and not caused by IPC/adaptive changes.

## SOLID-X

- [SOLID-X] No new violation found. The changes keep orchestration in `TwoPhaseNSSolver`, numerical stage logic in `ns_step_services`, and trigger policy in `PsiDirectTransport`.
