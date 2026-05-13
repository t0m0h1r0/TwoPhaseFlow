# CHK-RA-CH14-AO-FASTVOL-056 - Block-resident PCG for AO-Fast Schur solves

## Scope

User question: can PCG itself be fundamentally improved?

Target route:

- `experiment/ch14/diagnose_ao_stage_chain.py`
- `experiment/ch14/config/ch14_capillary.yaml`
- `--runner-initial-grid-rebuild --backend gpu`

## Theory

The AO-Fast projection solves the fixed-stratum normal equation

```text
S lambda = b,   S = J_A J_A^T
```

with Jacobi-preconditioned CG.  The previous GPU implementation preserved this
equation but drove it from Python: each PCG iteration launched Schur, dot
products, residual max, and vector updates as separate kernels.  Because the
Chapter 14 capillary wave uses `32 x 32 = 1024` cells, the whole Schur row space
fits in one CUDA block.  That permits a stronger GPU implementation without
changing the solver:

- one cell per thread;
- `x`, `r`, `z`, `p`, and `Ap` live in shared memory;
- dot products and `linf` tests are block reductions;
- the convergence/floor test is performed inside the device loop;
- early break is device-local and algebraically equivalent to the previous
  mask-frozen fixed loop.

For larger grids or non-CuPy backends the code falls back to the vector PCG
implementation.

## Implementation

Added `_solve_schur_pcg_block_raw_if_available` and a cached CuPy RawKernel
`solve_schur_pcg_block_2d`.  The public `_solve_schur_pcg_fixed_gpu` dispatches
to the block kernel when `n_cells <= 1024` and dtype is float32/float64;
otherwise it uses `_solve_schur_pcg_fixed_gpu_vector`.

The RawKernel uses the same P1 cell-node incidence formula for
`J_A J_A^T` as CHK-055 and keeps all nonuniform-grid/interface information in
`jq_local`.

## Validation

- Local syntax:
  - `python3 -m py_compile ...` PASS
- Remote tests:
  - `748 passed, 33 skipped`
  - includes RawKernel PCG vs vector PCG equality
- Remote 3-step cProfile:
  - after CHK-055: `19.478s`
  - after block PCG: `8.470s`
  - projection stage: `13.845s -> 3.284s`
- Remote 10-step capillary route:
  - PASS
  - after CHK-055: `real 0m53.508s`
  - after block PCG: `real 0m23.601s`
  - sampled GPU utilization included 66%, 48%, and 41% spikes; later samples
    remain lower because geometry refresh, swept-flux polygon cuts, and other
    small-kernel stages now dominate.

## Residual risk

The block PCG route is intentionally limited to `n_cells <= 1024`.  It is a
correct fundamental improvement for the current N=32 capillary-wave route.  For
N>32, a true multi-block PCG needs cooperative-grid synchronization or a
different solver/preconditioner design; silently applying this single-block
kernel there would be wrong.

## SOLID / fidelity notes

- [SOLID-S] Raw PCG dispatch is isolated from vector PCG fallback and Schur
  support construction.
- [SOLID-D] Solver dispatch depends on backend capability and row-space size,
  not on experiment names.
- [SOLID-X] No physical parameter, CFL, damping, smoothing, tolerance
  weakening, solver-iteration reduction, FD/WENO/PPE fallback, dense CPU
  fallback, nonuniform-grid removal, interface-tracking grid-rebuild removal,
  production YAML retuning, main merge, or branch deletion was introduced.
