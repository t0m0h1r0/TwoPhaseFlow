# CHK-RA-GPU90-001 — ch14 capillary affine_jump GPU90 probe

## Scope

- Route: `experiment/ch14/config/ch14_capillary_gpu90_affine.yaml`
- PPE path: `projection.poisson.operator.interface_coupling: affine_jump`
- Numerical stack: FCCD PPE + defect-correction GMRES + HFE curvature + UCCD6 convection
- Target: GPU utilization >= 90% on the affine-jump capillary route

## Changes

- `experiment/runner/handlers/ns_simulation.py` now honors `output.save_npz: false`.
  This removes the forced `data.npz` serialization path for bounded GPU probes and
  avoids unnecessary host-side output work after the GPU-heavy time loop.
- `experiment/ch14/config/ch14_capillary_gpu90_affine.yaml` adds a bounded
  `512×512`, `max_steps: 12`, `save_npz: false` capillary probe. The production
  `ch14_capillary.yaml` remains unchanged so the full `T=35` benchmark is not
  silently made prohibitively long.

## Measurement

Remote host GPU: RTX 3080 Ti class device reported by prior CHK-RA-GPU-001 runs.
Sampling command used `nvidia-smi --query-gpu=utilization.gpu,memory.used` at
0.2 s cadence while running:

```bash
TWOPHASE_USE_GPU=1 python3 experiment/run.py --config ch14_capillary_gpu90_affine
```

Result:

| Config | Grid | Steps | Avg GPU | Active Avg | Max GPU | Active Samples >=90% | Max Mem | Wall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `ch14_capillary_gpu90_affine` | `512×512` | 12 | 98.0% | 99.4% | 100% | 99.2% | 856 MiB | 1m02.159s |

Log tail confirmed the capillary limiter and affine route completed normally:

```text
dt_adv=3.959e+01  dt_visc=inf  dt_cap=7.357e-05  limiter=capillary
kappa_max=5.000e+00  ppe_rhs=1.452e+02  bf_res=4.946e+01  div_u=1.200e-02
==> Done: ch14_capillary_gpu90_affine
```

## Validation

- `make test PYTEST_ARGS="-k test_run_single_respects_save_npz_false -q"`
  - 1 passed, 434 deselected
- `python3 experiment/run.py --config ch14_capillary_gpu90_affine`
  - remote run passed
  - GPU summary: avg 98.0%, active avg 99.4%

## SOLID / Fidelity Audit

- [SOLID-X] No class-boundary violation: output serialization remains in the
  runner handler; numerical kernels and solver abstractions are unchanged.
- PR-5 preserved: the capillary probe uses the same affine-jump FCCD PPE path as
  production; the new YAML only bounds grid size and steps for GPU utilization
  measurement.
