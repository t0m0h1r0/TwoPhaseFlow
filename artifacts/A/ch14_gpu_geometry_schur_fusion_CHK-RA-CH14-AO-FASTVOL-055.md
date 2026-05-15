# CHK-RA-CH14-AO-FASTVOL-055 - GPU geometry/Schur fusion for capillary wave

## Scope

User request: apply a fundamental countermeasure for the Chapter 14 capillary
wave GPU optimization problem without weakening the physics, math, grid
rebuild, or AO-Fast contracts.

The target route is:

- `experiment/ch14/diagnose_ao_stage_chain.py`
- `experiment/ch14/config/ch14_capillary.yaml`
- `--runner-initial-grid-rebuild --backend gpu`

## Theory-first RCA

The measured 10-step route used the GPU but stayed around one saturated Python
core and roughly 20-30 percent GPU utilization.  cProfile showed the dominant
cost was not a hidden CPU fallback after the previous transfer cleanup.  The
cost was the active-geometry compatibility projection:

- fixed-shape Newton/PCG control repeatedly launched small CuPy kernels;
- line search recomputed full P1 geometry although the line-search theorem only
  needs exact `Q_h(phi)` residual monotonicity;
- Schur matvec evaluated the exact `J_A J_A^T` algebra through separate
  cell-to-node scatter and node-to-cell gather array operations.

The violated performance contract was therefore GPU work granularity, not the
physical capillary law, not the nonuniform grid, not interface-tracking grid
rebuilds, and not the AO-Fast PCG-only solver contract.

## Implemented countermeasures

1. Added exact active `Q_h`-only volume kernels:
   - `refresh_active_volume_geometry_2d`
   - `refresh_active_volume_geometry_candidates_2d`

   These reuse the same marching-squares cut-cell area formula as
   `refresh_active_geometry_2d`, but skip surface length and derivative tables
   where the equation only asks for volume residuals.

2. Batched the six fixed backtracking candidates in
   `_residual_reducing_step_gpu`.

   The accepted step remains the first candidate in
   `{1, 1/2, 1/4, 1/8, 1/16, 1/32}` that reduces exact `Q_h` residual.  The
   candidate set and acceptance rule are unchanged.

3. Replaced the hot-loop masked Schur apply with the direct P1 incidence formula
   and a CuPy RawKernel when available.

   For a cell value field `lambda`, the kernel computes
   `J_A J_A^T lambda` by summing active neighboring cell-corner contributions at
   each node and contracting with the current cell row.  Nonuniform-grid and
   interface-state dependence remain entirely in `jq_local`; the fused kernel
   does not assume uniform spacing or remove grid rebuilds.

## Validation

- Local syntax:
  - `python3 -m py_compile ...` PASS
- Remote test suite after q-only/batched/direct-Schur changes:
  - `746 passed, 33 skipped`
- Remote test suite after RawKernel Schur path:
  - `747 passed, 33 skipped`
- Remote 3-step cProfile:
  - before this CHK: `41.048 s`
  - q-only line search: `28.027 s`
  - batched q-only line search: `24.426 s`
  - RawKernel Schur fusion: `19.478 s`
- Remote 10-step capillary route:
  - PASS
  - `real 0m53.508s`
  - previous same route before this CHK was about `1m58s`
  - sampled GPU utilization was mostly in the high teens to 20s, with a 76
    percent spike; CPU settled near one Python core after startup.

## Residual risk

GPU utilization percentage is still bounded by the small `N=32` problem size,
the Python-level fixed Newton/PCG orchestration, global reductions in PCG, and
the swept-flux/FCCD/PPE stages outside this patch.  The important improvement is
that the same route now performs substantially less Python-mediated kernel
launch work while preserving the exact discrete algebra.

Further optimization should target device-side solver orchestration or larger
batched route execution, not tolerance weakening, CFL retuning, projection
frequency reduction, uniform-grid replacement, or disabling interface-tracking
grid rebuilds.

## SOLID / fidelity notes

- [SOLID-S] Volume-only geometry is separated from full geometry with
  derivatives; Schur fusion is isolated inside the masked support apply.
- [SOLID-D] The fused Schur path depends only on backend capabilities and the
  `jq_local` coefficient contract.
- [SOLID-X] No physical parameter, CFL, damping, smoothing, tolerance
  weakening, FD/WENO/PPE fallback, dense CPU fallback, nonuniform-grid removal,
  interface-tracking grid-rebuild removal, production YAML retuning, main merge,
  or branch deletion was introduced.
