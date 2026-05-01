# CHK-RA-GPU-UTIL-006 — FD direct vs weighted-CG L_L benchmark

Date: 2026-05-01
Branch/worktree: `ra-gpu-util-20260501` /
`.claude/worktrees/ra-gpu-util-20260501`

## Question

Evaluate the accuracy, GPU memory use, and compute-time relationship between
the factor-reused FD direct method and the optional weighted-CG method for the
defect-correction low-order `L_L` solve.

## Setup

- Command:
  `make cycle EXP=experiment/ch14/bench_fd_ll_solvers.py ARGS="--sizes 64,128,192 --cg-tols 1e-4,1e-6,1e-8 --rhs-count 3 --maxiter 3000 --output experiment/ch14/results/fd_ll_solver_bench/fd_ll_solver_bench.json"`
- Device: remote GPU via `TWOPHASE_USE_GPU=1`.
- Operator: conservative FD flux-form `L_L`, wall Neumann BC, gauge pin.
- Workload: 3 RHS for one fixed density field, matching one DC solve's
  initial/correction RHS reuse pattern.
- Direct path: factorize once, reuse factor for all RHS.
- CG path: weighted SPD system `-W L_L p = -W rhs`, Jacobi preconditioner.
- Memory metric: CuPy pool total is the solver-specific allocation proxy;
  process peak from `nvidia-smi` includes CUDA context/library overhead.

## Results

| N | method | tol | total s | mean/RHS s | pool MiB | proc peak MiB | rel err vs direct | rel residual | time/direct | pool/direct |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | FD direct | -- | 0.057 | 0.014 | 9.8 | 272 | 0 | 9.82e-15 | 1.00 | 1.000 |
| 64 | FD-CG | 1e-4 | 0.411 | 0.137 | 1.0 | 262 | 1.76e-4 | 1.00e-4 | 7.26 | 0.100 |
| 64 | FD-CG | 1e-6 | 0.499 | 0.166 | 1.0 | 262 | 9.18e-7 | 1.01e-6 | 8.82 | 0.100 |
| 64 | FD-CG | 1e-8 | 0.533 | 0.178 | 1.0 | 262 | 2.75e-8 | 9.89e-9 | 9.42 | 0.100 |
| 128 | FD direct | -- | 0.196 | 0.047 | 46.9 | 324 | 0 | 1.36e-14 | 1.00 | 1.000 |
| 128 | FD-CG | 1e-4 | 0.773 | 0.258 | 3.8 | 266 | 1.13e-3 | 9.85e-5 | 3.95 | 0.082 |
| 128 | FD-CG | 1e-6 | 0.944 | 0.315 | 3.8 | 266 | 2.98e-6 | 1.00e-6 | 4.82 | 0.082 |
| 128 | FD-CG | 1e-8 | 1.127 | 0.375 | 3.8 | 266 | 1.30e-8 | 9.80e-9 | 5.75 | 0.082 |
| 192 | FD direct | -- | 0.519 | 0.129 | 114.1 | 406 | 0 | 3.15e-14 | 1.00 | 1.000 |
| 192 | FD-CG | 1e-4 | 1.081 | 0.360 | 8.5 | 270 | 8.26e-4 | 1.01e-4 | 2.08 | 0.075 |
| 192 | FD-CG | 1e-6 | 1.445 | 0.482 | 8.5 | 270 | 1.76e-6 | 9.92e-7 | 2.78 | 0.075 |
| 192 | FD-CG | 1e-8 | 1.708 | 0.569 | 8.5 | 270 | 1.01e-8 | 9.99e-9 | 3.29 | 0.075 |

The benchmark script writes raw JSON to
`experiment/ch14/results/fd_ll_solver_bench/fd_ll_solver_bench.json`; the
generated results directory was not committed because it is an experiment
output cache.

## Interpretation

1. **Accuracy**
   - FD direct gives machine-level low-order residual (`~1e-14`).
   - FD-CG residual follows the requested tolerance.
   - If outer DC tolerance is `1e-8`, FD-CG should be run at about `1e-8`;
     `1e-6` introduces `O(1e-6)` pressure error relative to FD direct, and
     `1e-4` is too loose for paper-grade DC accuracy.

2. **Time**
   - For the current 2D ch14-scale workload, factor-reused FD direct is faster.
   - With 3 RHS per density field, FD-CG is `2.1x--9.4x` slower across the
     measured sizes.
   - The slowdown ratio decreases with N because direct factorization memory
     traffic grows faster, but no crossover appears by `N=192`.

3. **Memory**
   - FD-CG uses only `7.5%--10%` of the direct solver's CuPy pool allocation.
   - Direct pool allocation grows from `9.8 MiB` at `N=64` to `114.1 MiB` at
     `N=192`; CG grows from `1.0 MiB` to `8.5 MiB`.
   - Process peak includes CUDA context overhead, but still shows direct
     increasing from `272 MiB` to `406 MiB`, while CG stays near `262--270 MiB`.

## Decision

- Keep `fd/direct` as the default for existing ch14 capillary YAMLs and
  schedule=1 runs.
- Use FD-CG only when memory pressure dominates, or for larger/3D cases where
  direct factor memory becomes prohibitive.
- If FD-CG is selected inside DC, use weighted-CG (`-W L_L p=-W rhs`) with
  `preconditioner: jacobi` or `none`; do not use nonsymmetric line-PCR with CG.

## SOLID Audit

- `[SOLID-X]` no violation found.  The benchmark is additive and does not
  change production solver responsibilities or module boundaries.
