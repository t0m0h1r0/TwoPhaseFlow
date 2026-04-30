# CHK-RA-GPU-001 -- ch14 capillary affine_jump GPU optimization

## Scope

- Branch: `ra-gpu-affine-jump-opt-20260430`
- Worktree: `.claude/worktrees/ra-gpu-affine-jump-opt-20260430`
- Target route: `experiment/ch14/config/ch14_capillary.yaml` stack with
  `surface_tension: pressure_jump` and
  `projection.poisson.operator.interface_coupling: affine_jump`.
- Measurement host: `python`, NVIDIA GeForce RTX 3080 Ti.
- Probe method: temporary capillary YAML copied from `ch14_capillary.yaml`,
  with `run.time.max_steps: 24`, `output.snapshots: {}`, and `figures: []`.
  The solver route and `affine_jump` coupling stayed active.

## Code changes

1. `PPESolverDefectCorrection` now collapses redundant defect correction only
   when the base solver and target operator are the same `affine_jump` FCCD
   operator.  The single solve temporarily tightens the inner GMRES tolerance
   to the DC tolerance, preserving the linear solve target while avoiding
   repeated identical GMRES solves.
2. `prepare_fccd_matrixfree_operator()` skips the density host copy on GPU for
   `affine_jump`, where phase-mean gauge data are intentionally disabled.
3. CCD wall boundary closures avoid many tiny GPU `dgemv` calls by using fused
   explicit boundary linear combinations on GPU.  CPU behavior keeps the
   existing matrix-vector form.
4. CCD axis setup materializes `A_inv_dev_T`, enabling the existing transpose
   matmul path in `_solve_dense_inverse_or_lu()`.

## Remote measurements

Sampling command queried `nvidia-smi --query-gpu=utilization.gpu,memory.used`
every 0.2 s in the same SSH shell as the run.  The monitor process was killed
by the shell trap at run exit.

| Case | Grid cells | Elapsed | Samples | Avg GPU | Active GPU | >=50% active samples | Max memory |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 64 x 64 | 96.839 s | 423 | 30.5% | 30.8% | 0.0% | 298 MiB |
| Collapse DC only | 64 x 64 | 36.127 s | 158 | 28.5% | 29.1% | 0.0% | 298 MiB |
| Collapse + CCD boundary opt | 64 x 64 | 34.784 s | 152 | 26.0% | 26.9% | 0.0% | 298 MiB |
| Same affine route reachability probe | 256 x 256 | 36.431 s | 159 | 59.1% | 60.6% | 99.4% | 862 MiB |

Interpretation: the production-sized `64 x 64` capillary route is now 2.78x
faster for the 24-step probe, but remains too small to keep the RTX 3080 Ti
above 50% utilization.  The same `affine_jump` capillary route crosses the user
target at `256 x 256`, confirming the remaining utilization limit is small
problem size / kernel launch granularity rather than a CPU fallback in the
capillary coupling.

## Verification

- `make test PYTEST_ARGS="-k affine_jump -q"`: 7 passed, 427 deselected.
- `make test PYTEST_ARGS="-k defect_correction -q"`: 6 passed, 428 deselected.
- Direct remote targeted CCD/FCCD regression:
  `python -m pytest twophase/tests/test_ccd.py twophase/tests/test_fccd.py twophase/tests/test_fccd_convection.py twophase/tests/test_fccd_advection_levelset.py twophase/tests/test_defect_correction.py -q`
  -> 52 passed.
- `make test PYTEST_ARGS="-k ccd -q"` also exercised 143 passing selected tests,
  but still hit the pre-existing remote ch13 YAML absence for
  `ch13_capillary_water_air_alpha2_n128.yaml` and
  `ch13_rising_bubble_water_air_alpha2_n128x256.yaml`.

## SOLID audit

[SOLID-X] No violation found.  The performance changes stay inside existing
PPE/CCD boundaries, do not introduce cross-layer I/O dependencies, and keep
the `affine_jump` special case behind the existing coupling selector.
