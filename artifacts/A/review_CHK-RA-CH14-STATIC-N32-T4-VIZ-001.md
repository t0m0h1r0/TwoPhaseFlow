# CHK-RA-CH14-STATIC-N32-T4-VIZ-001

## Scope

User request: verify the static-droplet case at `N=32`, `T=4.0`, and do not forget visualization at `0.2` time intervals.

This is a validation-only run.  The temporary config was derived from `experiment/ch14/config/ch14_static_droplet.yaml` and changed only:

- `grid.cells: [32, 32]`
- `run.time.final: 4.0`
- `run.debug.step_diagnostics: true`
- `output.dir: results/_tmp_ch14_static_droplet_n32_t4_viz0p2`
- `output.snapshots.interval: 0.2`
- snapshot-series figures for `psi`, `velocity`, and `pressure_bulk`

The production numerical stack was unchanged: `face_implicit` curvature, no physical-time Ridge--Eikonal reinitialization for the static-equilibrium validation (`every_steps: 0`), `pressure_jump`, `affine_jump`, and `capillary_range_projection: range_projected`.

## Execution

Remote-first validation command:

```bash
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS="--config _tmp_ch14_static_droplet_n32_t4_viz0p2 --no-checkpoint-final"
```

Result:

- PASS
- remote runtime: `3m0.280s`
- pulled result directory: `experiment/ch14/results/_tmp_ch14_static_droplet_n32_t4_viz0p2`
- final time: `4.0`
- recorded steps: `405`

## Visualization Check

The `0.2` interval snapshot scheduler stores the first target after the first physical step, then stores each later target at the first CFL time that crosses it.  Therefore the actual file times are close to, but not exactly, multiples of `0.2`.

Pulled visualization files:

- `psi_t*.pdf`: 21 files
- `velocity_t*.pdf`: 21 files
- `pressure_bulk_t*.pdf`: 21 files
- time-series PDFs: `deformation.pdf`, `volume_drift.pdf`, `kinetic_energy.pdf`

Snapshot time coverage from `fields/times`:

- count: `21`
- first: `0.00988027197327`
- last: `4.0`
- min adjacent gap: `0.191859795407`
- max adjacent gap: `0.207717957263`

This satisfies the requested `0.2` visualization cadence under CFL time stepping.

## Numerical Metrics

From `data.npz`:

- `KE_initial = 1.979181e-38`
- `KE_final = 1.948632e-35`
- `KE_max = 1.948632e-35`
- `volume_drift_final = 1.776544e-15`
- `volume_drift_max_abs = 1.776544e-15`
- `deformation_final = 0.000000e+00`
- `deformation_max_abs = 0.000000e+00`
- `div_u_max = 1.769182e-17`
- `ppe_rhs_max = 3.952267e-15`
- `capillary_range_projection_linf_max = 2.784585e-02`
- `capillary_range_projection_solved_min = 1`
- `ppe_dc_converged_min = 1`
- `ppe_dc_iter_max = 12`
- `ppe_dc_rel_l2_max = 2.278601e-09`

## Verdict

PASS.  At `N=32`, `T=4.0`, the static droplet remains static to roundoff-level kinetic energy, preserves volume to roundoff, and keeps zero deformation.  PPE/DC convergence and incompressibility diagnostics are also within roundoff-level tolerances.

[SOLID-X] Validation/artifact/ledger only.  No production source, production YAML, damping, CFL workaround, curvature cap, smoothing, FD/WENO/PPE fallback, or alternate calculation scheme was introduced.
