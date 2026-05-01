# CHK-RA-GPU-UTIL-001 — ch14 capillary schedule=1 GPU utilization

## Scope

- Target YAML: `experiment/ch14/config/ch14_capillary.yaml`.
- User constraint: `grid.distribution.schedule: 1` is mandatory.
- Production semantics preserved: no schedule relaxation, no PPE tolerance relaxation, no paper-level algorithm substitution.

## Bottleneck evidence

Remote 12-step warm measurements used the existing ch14 capillary route with only temporary `max_steps`/output-trimming overrides.

| Case | Wall | GPU avg | Active avg | >=50% |
|---|---:|---:|---:|---:|
| schedule=1, diagnostics on, before | 27.734 s | 32.1% | 33.2% | 0.0% |
| schedule=1, diagnostics off, before | 28.625 s | 31.0% | 31.8% | 0.0% |
| schedule=1, diagnostics on, after | 11.716 s | 43.2% | 47.8% | 52.9% |

Longer 100-step confirmation after the change:

- Wall: 94.249 s
- GPU avg: 47.2%
- Active GPU avg: 48.1%
- >=50% samples: 58.5%
- >=80% samples: 0.7%
- max GPU memory: 1364 MiB

The main pre-change cProfile hot path was the matrix-free FCCD PPE/viscous matvec:

- `solve_gmres`: 30.354 s / 36 calls
- `PPESolverDefectCorrection.solve`: 23.316 s / 24 calls
- `fccd_matrixfree._apply_operator_core`: 20.760 s
- `ccd_solver_helpers.differentiate_ccd_wall_second_only`: 18.984 s
- `velocity_reprojector_basic.reproject`: 11.141 s

Diagnostics-off did not improve runtime, so debug D2H was not the dominant cost. `schedule=0` controls were faster, but are not admissible because schedule=1 is required.

## Analysis

The dominant issue was not a single large D2H/H2D transfer. It was many small GPU operations inside GMRES matvecs:

1. FCCD wall derivatives repeatedly solved the same compact derivative system for each matvec.
2. `schedule=1` rebuilds the interface-fitted grid every step and adds a neutral velocity reprojection PPE solve.
3. At `N=128`, the GPU workload is too small and too fragmented to saturate CU occupancy even after the derivative path is moved to denser matrix products.

## Paper-exact design

The wall CCD derivative is a linear operator for fixed grid and wall closure. Therefore the same discrete compact relation

`A q = B f + wall(f)`

can be algebraically pre-expanded once into derivative matrices `D1` and `D2`, then applied as `D f` on GPU. This changes only execution form, not the discretization. Nonuniform metric application is unchanged:

- first derivative: `J * d/dξ`
- second derivative: `J^2 * d²/dξ² + J * dJ/dξ * d/dξ`

Velocity reprojection is a neutral divergence repair solve, not an interface pressure-jump solve, so interface jump/stress context is cleared before reprojection PPE calls.

## Implementation

- Commit `09217ea5`: clear optional interface jump context before neutral reprojector PPE solves.
- Commit `d06537f4`: precompute GPU wall CCD derivative operator matrices and use them when no boundary override is active.

## Verification

- `make test PYTEST_ARGS='-k reprojector_ -q'` — 2 passed.
- `make test PYTEST_ARGS='-k ccd_derivative_gpu_matches_cpu --gpu -q'` — 1 passed.
- `make test PYTEST_ARGS='-k fccd_face_gradient_gpu_matches_cpu --gpu -q'` — 1 passed.

## Outcome and remaining path

The schedule=1 route improved from roughly 27.7 s to 11.7 s for the 12-step warm benchmark, a 2.37x wall-time speedup. GPU utilization improved from about 32% to 43–48%, but did not reach 80%.

The remaining 80% blocker is GMRES/FCCD granularity under `N=128` and schedule=1 dynamic reprojection, not the capillary YAML schedule itself. Further improvement should target fused FCCD matvec kernels or a more GPU-resident Krylov/preconditioner path while preserving the same pressure equation, jump formulation, CCD operators, and convergence tolerances.

[SOLID-X] no SOLID violation found.
