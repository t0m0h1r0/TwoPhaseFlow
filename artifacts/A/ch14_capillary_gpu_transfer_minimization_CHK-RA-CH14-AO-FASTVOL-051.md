# CHK-RA-CH14-AO-FASTVOL-051 - Ch14 Capillary GPU Transfer Minimization

## Scope

- User directive: optimize the route used by the current Chapter 14 capillary
  run, with D2H/H2D minimization and preferably zero hidden transfers as the
  first design principle.
- Route: `experiment/ch14/config/ch14_capillary.yaml`, active-geometry
  capillary runtime, PCG-only active projection.
- Non-negotiable contract: preserve the SP-AO/active-geometry algebra,
  nonuniform-grid metrics, interface-tracking grid rebuild contract, YAML
  solver tolerances, and fail-close gates.

## Theory-First Hypotheses

| Hypothesis | Test | Result |
|---|---|---|
| Dynamic active support discovery introduces synchronization or D2H-like control. | Forbid `argwhere`/`unique` in the fixed Schur route and solve a masked active problem. | Confirmed risk; replaced with fixed-shape masked support. |
| Repeated coordinate and metric conversions cause H2D churn on the hot path. | Search `xp.asarray(grid.coords/J/dJ_dxi)` in capillary, active geometry, and CCD helpers. | Confirmed; added grid device caches and routed hot calls through them. |
| Output or fail-close diagnostics dominate the measured route. | Keep scalar packet transfers only at explicit fail-close/reporting boundaries and run the shortened production route. | Some D2H remains by design, but cleanup did not materially reduce wall time. |
| Dynamic grid rebuild regular-stratum guard is still a host boundary. | Search `to_host`/`np.argwhere` in grid rebuild. | Confirmed remaining boundary; not changed because it belongs to the interface-tracking rebuild contract, not inner AO/FCCD kernels. |
| Transfer cleanup can change AO algebra. | Re-run component exactness and production smoke. | Falsified; exactness and run gates still pass. |

## Changes

- `src/twophase/simulation/geometric_phase_runtime_gpu.py`
  - Added fixed-shape masked Schur support for 2D active rows.
  - Routed PCG/DC/DC-then-PCG Schur matvecs through masked `J`, `J^T`, and
    `J J^T` operations.
  - Reused the support for capillary energy projection, normal residuals,
    q/phi compatibility projection, and pressure-reaction residuals.
  - Replaced repeated coordinate/cell-width conversions with grid device-cache
    accessors.
- `src/twophase/core/grid.py`
  - Added metric-epoch device caches for coordinates, cell widths, CCD metrics,
    and metric gradients.
  - Invalidated those caches whenever grid metrics are rebuilt.
  - Made `meshgrid` and the closure seed indicator use cached backend-native
    coordinates.
- `src/twophase/geometry/active_kernels.py`
  - Reused cached device coordinates for active-cell corner fields.
- `src/twophase/ccd/ccd_solver_helpers.py`
  - Reused cached device CCD metrics and metric gradients in nonuniform metric
    mapping.
- `src/twophase/tests/test_geometric_runtime_gpu_gates.py`
  - Added a regression that raises if fixed-shape Schur PCG calls dynamic
    `argwhere` or `unique`.

## Residual Transfer Boundaries

- `_host_scalar_packet_float` still performs one batched D2H packet at
  fail-close/reporting boundaries.  This is intentional and outside the Krylov
  recurrence.
- `Grid.update_from_levelset` still materializes the rebuilt level-set field on
  host for the regular-stratum guard and uses host `np.argwhere`.  This is the
  next theoretical boundary if a fully device-side grid-rebuild guard becomes
  necessary.
- Final result serialization and plotting still transfer data to host.

## Validation

```text
python3 -m py_compile \
  src/twophase/core/grid.py \
  src/twophase/ccd/ccd_solver_helpers.py \
  src/twophase/geometry/active_kernels.py \
  src/twophase/simulation/geometric_phase_runtime_gpu.py \
  src/twophase/tests/test_geometric_runtime_gpu_gates.py
PASS
```

```text
make test PYTEST_ARGS="-k ccd_derivative_gpu_matches_cpu --gpu -q"
1 passed, 943 deselected
```

```text
make test PYTEST_ARGS="twophase/tests/test_geometric_runtime_gpu_gates.py -q"
739 passed, 33 skipped
```

```text
make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py \
  ARGS="--scheme pcg --max-pcg-iterations 256"
schur_pcg active_residual_linf 8.2124281333695315e-13 PASS
capillary_riesz raw_face_covector_linf_diff 3.5860203695392556e-13 PASS
gpu normal residual checks PASS
```

```text
make run EXP=experiment/ch14/diagnose_ao_gpu_theory_probe.py \
  ARGS="--config experiment/ch14/config/ch14_capillary.yaml --steps 2"
PASS, real 0m24.810s
```

```text
make cycle EXP=experiment/run.py \
  ARGS="--config ch14_capillary --final-time 0.000171430986 --no-checkpoint-final"
PASS, real 2m1.400s
```

`git diff --check` passed after the code changes.

## Verdict

The transfer-first optimization removed hidden dynamic-support discovery and
repeated coordinate/metric H2D conversions from the capillary active-geometry
hot route while preserving the exact discrete algebra.  The shortened
production route still runs at roughly the same wall time, so the dominant cost
is no longer explained by these transfer boundaries alone.  The next
performance work should target algebra-preserving fusion or residency in the
remaining numerical kernels, especially FCCD/PPE/viscous matvec work or the
interface-tracking grid-rebuild guard, not physics retuning.

## SOLID / Fidelity Audit

- [SOLID-S] Grid owns device-coordinate and metric caches; AO runtime only asks
  for backend-native grid data.
- [SOLID-D] Schur solvers depend on a support interface that preserves `J`,
  `J^T`, and `J J^T`, not on a concrete compact-index implementation.
- [SOLID-X] No physical parameter change, CFL reduction, smoothing, damping,
  tolerance weakening, FD/WENO/PPE fallback, dense CPU fallback, hidden solver
  fallback, arbitrary coordinate offset, main merge, or branch deletion was
  introduced.
