# CHK-RA-CH14-STATIC-N64-T1-VIZ-001

## Scope

User request: run the same static-droplet validation at `N=64`, `T=1.0`, with visualization every `0.2` time units.

This is a validation-only run.  The temporary config was derived from `experiment/ch14/config/ch14_static_droplet.yaml` and changed only:

- `grid.cells: [64, 64]`
- `run.time.final: 1.0`
- `run.debug.step_diagnostics: true`
- `output.dir: results/_tmp_ch14_static_droplet_n64_t1_viz0p2`
- `output.snapshots.interval: 0.2`
- snapshot-series figures for `psi`, `velocity`, and `pressure_bulk`

The production numerical stack was unchanged: `face_implicit` curvature, no physical-time Ridge--Eikonal reinitialization for the static-equilibrium validation (`every_steps: 0`), `pressure_jump`, `affine_jump`, and `capillary_range_projection: range_projected`.

## Execution

Remote-first validation command:

```bash
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS="--config _tmp_ch14_static_droplet_n64_t1_viz0p2 --no-checkpoint-final"
```

Result:

- PASS
- remote runtime: `5m49.301s`
- pulled result directory: `experiment/ch14/results/_tmp_ch14_static_droplet_n64_t1_viz0p2`
- final time: `1.0`
- recorded steps: `309`

## Visualization Check

The `0.2` interval snapshot scheduler stores each target at the first CFL time that crosses it, so actual file times are close to the requested cadence.

Pulled visualization files:

- `psi_t*.pdf`: 6 files
- `velocity_t*.pdf`: 6 files
- `pressure_bulk_t*.pdf`: 6 files
- time-series PDFs: `deformation.pdf`, `volume_drift.pdf`, `kinetic_energy.pdf`

Snapshot time coverage from `fields/times`:

- count: `6`
- first: `0.00323530429583`
- last: `1.0`
- min adjacent gap: `0.197131837377`
- max adjacent gap: `0.200718104933`

This satisfies the requested `0.2` visualization cadence under CFL time stepping.

## Numerical Metrics

From `data.npz`:

- `KE_initial = 6.166935e-39`
- `KE_final = 9.445160e-37`
- `KE_max = 9.445160e-37`
- `volume_drift_final = 1.373859e-16`
- `volume_drift_max_abs = 4.121576e-16`
- `deformation_final = 0.000000e+00`
- `deformation_max_abs = 0.000000e+00`
- `div_u_max = 2.189963e-17`
- `ppe_rhs_max = 1.655695e-14`
- `capillary_range_projection_linf_max = 5.803505e-02`
- `capillary_range_projection_solved_min = 1`
- `ppe_dc_converged_min = 1`
- `ppe_dc_iter_max = 12`
- `ppe_dc_rel_l2_max = 2.208135e-09`

## Verdict

PASS.  At `N=64`, `T=1.0`, the static droplet remains static to roundoff-level kinetic energy, preserves volume to roundoff, and keeps zero deformation.  PPE/DC convergence and incompressibility diagnostics are also within roundoff-level tolerances.

[SOLID-X] Validation/artifact/ledger only.  No production source, production YAML, damping, CFL workaround, curvature cap, smoothing, FD/WENO/PPE fallback, or alternate calculation scheme was introduced.
