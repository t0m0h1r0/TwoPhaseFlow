# CHK-RA-CH14-VAR-059 - Corrected PhaseRegion Graph YAML One-Period Run

Date: 2026-05-17

Scope: correct the previous old-route mistake and run the capillary wave for one
period on the new PhaseRegion graph route.

## Correction

CHK-RA-CH14-VAR-058 used the legacy production `experiment/run.py --config
ch14_capillary` route.  That was not the route requested by the user.

The requested new route is the reduced PhaseRegion graph route:

```text
eta -> q_l = Q_h(eta)
q_g = |C| - q_l
PhaseRegionBatch(GAS_ABOVE graph)
E_h graph-perimeter second-variation modal step
```

## YAML Update

Canonical capillary entry point:

```text
experiment/ch14/config/ch14_capillary.yaml
```

This YAML is a wrapper around the retained legacy physical/grid base config:

```text
base_config: legacy/ch14_capillary_legacy_runtime.yaml
phase_region_graph:
  owner: gas_above
  chart: graph_periodic
  q_measurement: exact_graph_column_integral
  phase_owner_map: exact_complement
  energy: graph_perimeter_second_variation
  dynamics: velocity_verlet_linear_capillary_mode
  backend:
    use_gpu: true
  run:
    periods: 1.0
    steps_per_period: 2560
```

Updated:

```text
experiment/ch14/diagnose_phase_region_capillary_graph_steps.py
```

The script now reads `phase_region_graph.run.periods`,
`phase_region_graph.run.steps_per_period`, and
`phase_region_graph.backend.use_gpu` from the wrapper YAML.  The command no
longer needs `--steps`, `--dt`, or `--use-gpu` to run the new route for one
period.

The old production-runtime config is retained for regression at:

```text
experiment/ch14/config/legacy/ch14_capillary_legacy_runtime.yaml
```

## Remote Experiment

Command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml'
```

Result: PASS.

```text
phase_region_graph_steps_admitted = 1
steps                             = 2560
dt                                = 1.825897807156e-05
t_final                           = 4.674298386319e-02
t_over_T                          = 1.000000000000e+00
step_backend_gpu                  = 1
q_measurement_fast_column_integral= 1
max_amplitude_error               = 2.416836235604e-10
max_velocity_error                = 4.456387104473e-08
max_energy_drift                  = 1.505982113082e-06
max_residual_l2                   = 0.000000000000e+00
max_volume_drift                  = 5.421010862428e-20
max_step_wall_seconds             = 3.977783117443e-02
mean_step_wall_seconds            = 3.516834525792e-03
target_met                        = 1
final_amplitude                   = 1.999999999998e-04
final_exact_amplitude             = 2.000000000000e-04
force_admissible                  = 0
```

Outputs:

```text
experiment/ch14/results/diagnose_phase_region_capillary_graph_steps/data.npz
experiment/ch14/results/diagnose_phase_region_capillary_graph_steps/phase_region_capillary_graph_steps.pdf
```

Rendered preview:

```text
/private/tmp/phase_region_capillary_graph_new_route_one_period_gpu.png
```

## Boundary

This is the new reduced PhaseRegion graph route.  It is not the legacy
production `experiment/run.py` route, and it still does not connect a
PhaseRegion face cochain to production pressure/velocity state.  Therefore
`force_admissible=0` remains correct.

[SOLID-X] Canonical capillary filename now points to the new PhaseRegion graph
wrapper; the old production runtime config is retained under `config/legacy/`.
Route-YAML parsing in the diagnostic experiment,
artifact/wiki/ledger, and experiment execution only; no physical parameter,
CFL, damping, smoothing, tolerance weakening, rebuild skipping, FD/WENO/PPE
fallback, hidden CPU fallback, production pressure/velocity coupling, main
merge, branch deletion, worktree removal, or origin push changed.
