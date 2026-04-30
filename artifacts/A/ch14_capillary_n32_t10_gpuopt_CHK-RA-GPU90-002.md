# CHK-RA-GPU90-002 — ch14 capillary N32 T10 affine GPU route

## Scope

- Base YAML: `experiment/ch14/config/ch14_capillary.yaml`
- Probe YAML: `experiment/ch14/config/probes/ch14_capillary_n32_t10_affine_gpu.yaml`
- Route: `N=32`, `T=10`, `interface_coupling: affine_jump`
- Goal: average GPU utilization > 50%

## Main Intake

Before measuring this route, the worktree was fast-forwarded to latest
`origin/main`:

- Latest main: `0681f4a4` (`merge: ch14 oriented affine jump contract`)
- Prior N32/T10 artifact `CHK-RA-CH14-010` stopped at `t=4.8825` before the
  oriented affine-jump fix.

## Route Optimization

- The probe keeps the production capillary numerical stack unchanged:
  FCCD PPE, defect-correction GMRES, HFE curvature, UCCD6 convection, and
  affine interface-stress coupling.
- Probe output is GPU-measurement oriented: `save_npz: false`, `snapshots: {}`,
  and `figures: []`. This avoids post-run host serialization/plotting from
  diluting utilization measurements.
- The YAML is placed under `experiment/ch14/config/probes/`, which is resolvable
  by `experiment/run.py --config probes/...` but excluded from `--all`.

## Measurement

Command:

```bash
TWOPHASE_USE_GPU=1 python3 experiment/run.py --config _ra_gpu90_n32_t10_base
```

Sampling:

- `nvidia-smi --query-gpu=utilization.gpu,memory.used`
- Cadence: `0.2 s`

Result:

| Route | Grid | T | Status | Wall | Avg GPU | Active Avg | Max GPU | Active Samples >=50% | Max Mem |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| N32/T10 affine | `32×32` | 10.0 | pass | 44m25.610s | 81.1% | 81.1% | 99% | 76.6% | 607 MiB |

Log tail:

```text
step= 1500  t=8.3730  dt=0.00558  KE=2.082e-03
dt_adv=7.241e-02  dt_visc=inf  dt_cap=5.582e-03  limiter=capillary
kappa_max=5.000e+00  ppe_rhs=1.875e+00  bf_res=1.532e+01  div_u=4.991e-04
==> Done: _ra_gpu90_n32_t10_base
```

## Profile Check

Short N32 profile (`max_steps: 40`) showed the route is still dominated by
backend GMRES matvec work, not output:

| Cumulative hotspot | Time |
|---|---:|
| `gmres_helpers.solve_gmres` | 62.934 s |
| GMRES matvec interface | 60.056 s |
| pressure stage | 38.996 s |
| `fccd_matrixfree._apply_operator_core` | 34.677 s |
| `differentiate_ccd_wall_second_only` | 34.020 s |
| `fccd.face_gradient` | 31.314 s |
| predictor stage | 24.551 s |

## Verdict

- Primary goal achieved: average GPU utilization is `81.1%`, above the `50%`
  target.
- No additional numerical-kernel patch was applied in this checkpoint: after
  latest main's oriented affine-jump correction, the small-grid route is already
  GPU-saturated enough, and loosening solver tolerances or changing the
  algorithm would violate PR-5 without a separate accuracy study.

## Validation

- Full remote route run passed with status `0`.
- `git diff --check` passed.

[SOLID-X] No production class/module boundary violation. The committed change is
a probe YAML + documentation/artifact; numerical algorithm behavior remains
paper-exact.
