# CHK-RA-CH14-VAR-063 — Ch14 capillary YAML owns time and output fields

Date: 2026-05-17

## User Correction

The prior `ch14_capillary.yaml` wrapper was too thin and the output contract was
wrong.  The canonical YAML must own physical-time output timing and must not
hide important `interface`, `numerics`, `phi`, velocity, or pressure
specifications in the legacy file.

## Changes

- `experiment/ch14/config/ch14_capillary.yaml` now explicitly contains
  `grid`, `interface`, `physics`, `run`, `numerics`, `output`, `diagnostics`,
  `initial_condition`, `initial_velocity`, and `boundary_condition`.
- Time stepping is specified by `run.time.final=0.046742983863` and
  `run.time.cfl=1.0`; there is no fixed `run.time.dt`.
- Output times are specified by physical time:
  `[0, T/4, T/2, 3T/4, T]`.
- YAML output figures include signed amplitude, volume drift, kinetic energy,
  `phi`, velocity, pressure, and the PhaseRegion graph summaries.
- The PhaseRegion graph experiment derives its internal step count from the
  capillary CFL bound and maps YAML snapshot times to nearest step indices.
- Snapshot diagnostics now store `phi_snapshots`, `u_snapshots`,
  `v_snapshots`, `pressure_snapshots`, and `rho_snapshots` on the same node
  grid.  The velocity snapshot axis ticks are shared with `phi` and pressure.

## Clean Run

Before the final run, both local and remote `experiment/ch14/results` were
deleted.  The rerun used:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml'
```

Observed metrics:

```text
steps                  = 3103
dt                     = 1.506380401644e-05
cfl                    = 1.0
t_final                = 4.674298386300e-02
t_over_T               = 9.999999999959e-01
max_amplitude_error    = 1.644990574895e-10
max_velocity_error     = 3.033187518861e-08
max_energy_drift       = 1.025028838090e-06
max_residual_l2        = 0
max_volume_drift       = 5.421010862428e-20
max_step_wall_seconds  = 3.863535495475e-02
target_met             = 1
force_admissible       = 0
```

Result directory contains only the new route output:

```text
experiment/ch14/results/diagnose_phase_region_capillary_graph_steps/
```

The old route directory is absent:

```text
experiment/ch14/results/ch14_capillary  # absent
```

## Validation

- `py_compile` PASS for the Ch14 PhaseRegion graph script and snapshot plotting.
- Remote targeted tests PASS:
  - `-k ch14_capillary_yaml`
  - `-k ch14_canonical_yamls_use_theory_cfl_not_fixed_dt`
- NPZ audit PASS for `cfl=1.0`, 5 snapshot times, and
  `phi/u/v/pressure/rho` arrays with matching `(5, 33, 33)` shape.

## SOLID-X

This correction changes the canonical reduced PhaseRegion graph route,
its YAML-owned output contract, tests, paper figures, wiki, and artifact only.
It does not admit the production force path: `force_admissible=0` remains.
No tolerance weakening, damping, smoothing, curvature cap, CFL retuning as a
fix, rebuild skipping, FD/WENO/PPE fallback, or hidden CPU fallback was added.
