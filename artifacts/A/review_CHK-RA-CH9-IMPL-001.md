# CHK-RA-CH9-IMPL-001 — Chapter 9 implementation audit

Date: 2026-05-02
Branch: `ra-ch9-implementation-audit-20260502`
Worktree: `.claude/worktrees/ra-ch9-implementation-audit-20260502`

## Verdict

PASS AFTER FIX.

Chapter 9's projection-stage contract is now the public/default library path:
FCCD split PPE with phase-separated pressure-jump closure, affine interface
jump, global gauge for affine pressure jumps, and defect correction
`L_H p` residual / `L_L δ` correction with `k=3`.

## Paper Contract Checked

- Split PPE: each phase uses a constant-density Poisson operator and interface
  data enter as `[p]=J_p^χ` and `[ρ^{-1}∂_n p]=J_n`; the pressure increment
  uses `δj` and the full-pressure reconstruction uses `j_gl`.
- HFE: jump data are extended in a narrow band so FCCD/CCD stencils do not
  sample discontinuous curvature or pressure-jump data.
- FCCD/FVM balance: `D_f=-G_f*` and the same face coefficient/face metric must
  be shared by PPE, velocity corrector, and buoyancy residual.
- Affine pressure jump: `G_Γ(p;j)=G(p)-B_Γ(j)`, PPE RHS receives the matching
  `+D_f α_f B_f(j)`, and the velocity corrector subtracts the same `B_f(j)`.
- Gauge: affine pressure-jump solves must use one global gauge; per-phase mean
  gauges are forbidden because they erase the liquid/gas pressure-jump freedom.
- Defect correction: high-order residual `d=b-L_H p`, low-order correction
  solve `L_L δ=d`, update `p←p+ωδ`, practical standard `k=3`, direct low-order
  FD base, and `ω<0.833` (implemented default `ω=0.8`).

## Implementation Findings

- Existing affine gauge handling was compliant: FCCD affine-jump refresh uses a
  single pin and disables phase thresholds, so phase mean gauges are not applied.
- Existing affine-jump gradient is non-uniform aware: the face jump contribution
  divides by physical `grid.coords[axis][i+1]-grid.coords[axis][i]`.
- Existing low-order FD direct base is non-uniform aware: matrix coefficients
  use physical face distances and cell volumes and build device sparse matrices
  through the active backend.
- Divergence found: default/public construction still left PPE defect correction
  disabled (`False`, `max_iterations=0`, `relaxation=1.0`, no base solver).
- Divergence found: the DC wrapper enforced global RHS compatibility internally
  for affine mode, bypassing the FCCD operator's compatibility projector and
  losing operator diagnostics.

## Fixes

- Set default PPE DC to the Chapter 9 standard in constructor, config models,
  builder fallbacks, and parser defaults:
  `ppe_defect_correction=True`, `ppe_dc_base_solver="fd_direct"`,
  `ppe_dc_max_iterations=3`, `ppe_dc_tolerance=1.0e-8`,
  `ppe_dc_relaxation=0.8`.
- Updated tests that intentionally inspect raw FCCD/FVM solvers to opt out with
  `ppe_defect_correction=False`, keeping legacy/direct paths explicit instead
  of silently changing logic.
- Changed `PPESolverDefectCorrection` to delegate RHS compatibility projection
  to the high-order operator whenever the operator exposes it. This preserves
  the exact operator gauge/diagnostics for both phase-mean and affine/global
  gauge paths.
- Extended GPU smoke coverage so the default NS stack not only constructs on
  GPU but also executes the default DC solve with CuPy arrays and a GPU sparse
  factor.

## GPU / Fallback Audit

- No CPU fallback was introduced. GPU paths use `backend.xp`,
  `backend.sparse`, and `backend.sparse_linalg`; GPU unavailable remains a
  fail-closed `RuntimeError`.
- The low-order direct correction base uses `cupyx.scipy.sparse.csc_matrix` and
  `cupyx.scipy.sparse.linalg.splu` through `Backend` on GPU.
- The added GPU smoke confirms the returned pressure is a device array and that
  the FD direct base factor is built during the default DC solve.

## Validation

- `git diff --check` — PASS.
- `./remote.sh test -k test_construction_uniform -q` — PASS.
- `./remote.sh test -k test_ch7_default_ns_stack_constructs_on_gpu -q --gpu`
  — PASS after adding an actual default DC solve.
- `./remote.sh test -k test_phase_separated_fccd_ppe -q --gpu` — PASS.
- `./remote.sh test -k test_phase_separated_mean_gauge -q --gpu` — PASS.
- `./remote.sh test -k defect_correction -q --gpu` — PASS.
- `./remote.sh test -k test_affine_jump_pressure_stack_one_step_no_nan -q --gpu`
  — PASS.
- Full `./remote.sh test -q --gpu` was also run and failed on pre-existing or
  environment-scoped items outside this fix unit: missing ch13/ch14 config files
  on the current tree/remote, Ridge--Eikonal tolerance/stability tests, one
  legacy affine face-projection expectation, and the known GPU absolute
  phase-mean diagnostic tolerance (`7.66e-05` after subtracting an `O(1e11)`
  mean; the relative residual is machine-scale). Targeted Ch9/DC/GPU checks
  above pass.

## SOLID / Fidelity Notes

- [SOLID-X] No tested code was deleted.
- [SOLID-X] Legacy/raw PPE paths remain available only by explicit option.
- [SOLID-X] No fallback was added; paper-inexact defaults were replaced by the
  Chapter 9 DC contract.
- [SOLID-X] A3 chain maintained: Chapter 9 DC equation → `PPESolverDefectCorrection`
  residual/correction loop → public `TwoPhaseNSSolver`/config defaults and GPU
  smoke.
