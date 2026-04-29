# CHK-RA-CH14-002 ch14 GPU optimization measurement

## Scope

- Branch: `ra-ch14-gpu-opt-retry-20260429`
- id_prefix: `RA-CH14`
- Target: ch14 YAML main route, especially the shared Rayleigh-Taylor stack
  `FCCD PPE + pressure_jump + HFE + UCCD6 + Ridge-Eikonal + defect correction`.
- Measurement host: `python`, NVIDIA GeForce RTX 3080 Ti.
- Measurement method: 24-step Rayleigh-Taylor probe copied from
  `experiment/ch14/config/ch14_rayleigh_taylor.yaml`, with only
  `run.time.max_steps: 24`, `output.snapshots.times: []`, and no figures.
  This keeps the solver main route active while avoiding full final-time cost.

## Root cause

`build_fccd_interface_jump_context()` eagerly copied both `psi` and `kappa`
from device to host on every `set_interface_jump_context()` call. In the ch14
defect-correction PPE route this call is forwarded to both the base solver and
the operator, so the eager copy cost per step is:

| YAML | Node shape | Eager D2H bytes per step |
|---|---:|---:|
| `ch14_capillary.yaml` | 129 x 129 | 532,512 B = 0.51 MiB |
| `ch14_rising_bubble.yaml` | 129 x 257 | 1,060,896 B = 1.01 MiB |
| `ch14_rayleigh_taylor.yaml` | 129 x 513 | 2,117,664 B = 2.02 MiB |

Formula: `2 solvers x 2 arrays x nodes x 8 bytes`. The GPU solve path uses the
device arrays directly, so the host copies are only needed when a CPU pressure
array later enters `apply_interface_jump()`.

## Change

- `src/twophase/ppe/fccd_matrixfree_helpers.py` now stores host copies as
  `None` and materializes them lazily only in the host-pressure branch of
  `apply_fccd_interface_jump()`.
- Device-pressure behavior is unchanged:
  `p = p_tilde + sigma * kappa * (1 - psi)` still runs on `backend.xp`.
- CPU behavior is unchanged because the host branch materializes the same
  NumPy arrays before applying the jump.

## Remote GPU measurements

Sampling command used `nvidia-smi --query-gpu=utilization.gpu,memory.used`
every 0.2 s in the same SSH shell as the run; a shell `trap` killed the monitor
at exit. Final process check showed no remaining monitor or experiment process.

| Case | Elapsed | Samples | Avg GPU | Active GPU | >=50% active samples | Max memory |
|---|---:|---:|---:|---:|---:|---:|
| Clean baseline | 118.590 s | 515 | 77.6% | 78.1% | 99.6% | 670 MiB |
| Lazy host copies | 116.986 s | 508 | 78.6% | 79.2% | 99.6% | 644 MiB |

Delta: elapsed time improved by 1.35%, average GPU utilization improved by
1.0 percentage point, and the measured active-memory average remained well
above the user target of 50%.

## Verification

- `make test PYTEST_ARGS='-k pressure_jump'`: 8 passed, 416 deselected.
- Post-patch RT probe tail preserved the same CFL limiter and diagnostics:
  `dt_cap=3.867e-04`, `limiter=capillary`, `kappa_max=5.000e+00`,
  `ppe_rhs=1.307e+02`, `bf_res=1.040e+03`, `div_u=9.777e-06`.

## SOLID audit

[SOLID-X] No violation found. The patch is localized to a PPE helper and does
not merge I/O with computation or introduce a new high-level dependency on a
concrete implementation.
