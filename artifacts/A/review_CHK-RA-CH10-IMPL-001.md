# CHK-RA-CH10-IMPL-001 — Chapter 10 implementation audit

Date: 2026-05-02
Branch: `ra-ch10-implementation-audit-20260502`
Worktree: `.claude/worktrees/ra-ch10-implementation-audit-20260502`

## Verdict

PASS AFTER FIX.

Chapter 10 implementation is paper-consistent after two code fixes:

1. The public/direct non-uniform-grid default is now static (`grid_rebuild_freq=0`), matching the Chapter 10 standard path.
2. Non-uniform Ridge--Eikonal ridge extraction now uses physical-space CCD Hessians and rejects the former low-order Hessian fallback.

No paper change was needed: the Chapter 10 statements are internally consistent and the divergences were implementation-side.

## Paper Requirements Checked

- Fixed-grid non-uniform path: generate the interface-fitted grid from the initial interface and keep `ε_Γ` fixed. Dynamic tracking is not the standard path unless ALE/remap/history consistency is explicitly supplied.
- Composite monitor: `M_a = 1 + A_{\Gamma,a} I_{\Gamma,a} + A_{W,a} I_{W,a}` with wall refinement only on physical-wall axes.
- Metrics: non-uniform derivatives use computational-space CCD metrics (`J=dξ/dx`, `∂ξJ`) and must not substitute low-order metric formulas.
- FCCD non-uniform faces: central face uses the physical spacing `H_i=x_i-x_{i-1}` with `μ=0`, `λ=1/24`, and the same face geometry for BF/jump source terms.
- Ridge--Eikonal D1--D4:
  - D1 `σ_eff(x)=σ0 h(x)/h_ref`, `h=sqrt(hx hy)`.
  - D2 physical-space Hessian is evaluated directly by non-uniform CCD.
  - D3 FMM uses accepted-set causal ordering with physical upwind quadratic updates.
  - D4 `ε_local = ε_scale (ε/h_min) h(x)`.

## Implementation Findings

- `src/twophase/core/grid.py`: composite monitor, wall-axis selection, and fixed-coordinate equidistribution match Chapter 10. Periodic axes do not receive wall-layer refinement unless configured as physical walls.
- `src/twophase/core/metrics.py`: non-uniform metrics require `CCDSolver`; low-order metric substitution is rejected.
- `src/twophase/ccd/fccd.py` and `src/twophase/ccd/fccd_helpers.py`: non-uniform FCCD central face uses per-face physical `H_i` and the Chapter 10 `1/24` correction.
- `src/twophase/levelset/ridge_eikonal_reinitializer.py`: D1/D4 fields are `sqrt(hx hy)`-based, and FMM uses `NonUniformFMM`.
- `src/twophase/levelset/ridge_eikonal_fmm.py`: CPU/GPU paths both preserve accepted-set ordering; GPU runs the heap/candidate loop on device arrays rather than replacing it with fixed sweeps.

## Fixes Applied

- Static non-uniform default:
  - `src/twophase/simulation/ns_solver_options.py`
  - `src/twophase/simulation/config_models.py`
  - `src/twophase/simulation/ns_pipeline.py`
  - `src/twophase/simulation/ns_solver_builder.py`
- Physical CCD Hessian for non-uniform ridge extraction:
  - `src/twophase/levelset/ridge_eikonal_extractor.py`
  - `src/twophase/levelset/ridge_eikonal_reinitializer.py`
- Regression tests:
  - `src/twophase/tests/test_ridge_eikonal.py`
  - `src/twophase/tests/test_ns_pipeline.py`

## A3 Traceability

- Equation: Chapter 10 D2 requires the physical Hessian of `ξ_ridge`, not a computational-space or low-order substitute.
- Discretization: `CCDSolver.differentiate(xi, axis)` supplies physical first/second derivatives after the non-uniform metric transform; `first_derivative(gx, 1)` supplies the mixed physical derivative.
- Code: `RidgeExtractor.extract_ridge_mask()` now calls CCD for `gx,hxx`, `gy,hyy`, and `hxy` whenever `ccd` is provided; non-uniform grids without CCD raise `ValueError`.

## GPU Check

- Ridge extraction keeps arrays in `backend.xp` and returns a CuPy device mask on GPU.
- The changed Hessian path uses `CCDSolver` GPU operations instead of host finite-difference fallback.
- Existing GPU FMM accepted-set parity still passes, confirming no replacement by a fixed-sweep proxy.

## Validation

- `git diff --check` — PASS
- `./remote.sh push` — PASS
- `./remote.sh test -k test_nonuniform_ridge_extraction_requires_ccd --gpu` — PASS (`2 passed`)
- `./remote.sh test -k test_nonuniform_ridge_extraction_uses_ccd --gpu` — PASS (`2 passed`)
- `./remote.sh test -k test_construction_nonuniform --gpu` — PASS (`1 passed`)
- `./remote.sh test -k test_gpu_nonuniform_ridge_extraction_stays_on_device --gpu` — PASS (`1 passed`)
- `./remote.sh test -k test_gpu_parity_ridge_kernels --gpu` — PASS (`1 passed`)
- `./remote.sh test -k test_gpu_fmm_matches_cpu_accepted_set_with_ridge_seeds --gpu` — PASS (`1 passed`)

An accidental broad remote pytest collected the full suite and failed on existing out-of-scope items: missing ch13/ch14 config files on remote, Ridge--Eikonal stability/tolerance tests, one legacy face-projection expectation, phase-mean diagnostic tolerance, and split-reinit y-flip tolerance. The targeted Chapter 10/GPU validations above all pass.

## SOLID-X

No tested code was deleted. The change removes a paper-inexact non-uniform fallback and centralizes the Chapter 10 Hessian contract in `RidgeExtractor`; legacy uniform behavior remains explicit and unchanged.
