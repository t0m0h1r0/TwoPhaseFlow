# CHK-RA-CH14-VAR-055 - PhaseRegion Graph GPU Hot Path

Date: 2026-05-17

Scope: optimize the reduced PhaseRegion capillary-wave graph route so the GPU
path reaches the target `0.2 s/step` without changing the physical route.

## Target Route

The route remains:

```text
eta -> q_l = Q_h(eta)
q_g = |C| - q_l
PhaseRegionBatch(GAS_ABOVE graph)
assemble_phase_region_measurement(...)
linearized E_h second-variation modal step
```

The optimization changes the representation of this same route, not the
equation being checked.

## Implemented Optimization

Added a GPU-capable exact graph measurement helper:

```text
graph_q_from_eta_column_integral(grid, eta_nodes)
```

For each cell column it computes the exact P1 graph cell measure by integrating
the positive part of the linear segment:

```text
q_ij = integral_x [(eta(x) - y_j)_+ - (eta(x) - y_{j+1})_+] dx
```

This avoids the per-cell scalar polygon/reconstruction loop in the graph
few-step experiment and keeps the hot path on `backend.xp`.

The PhaseRegion measurement and phase-owner map were also made device-aware:

```text
map_cell_measure_to_phase_owner(...)
assemble_phase_region_measurement(...)
```

They now preserve device arrays for `q_g`, component reductions, residuals, and
volume/perimeter diagnostics, with explicit scalar host boundaries only for
reported diagnostics.

The experiment gained:

```text
--use-gpu
step_backend_gpu
q_measurement_fast_column_integral
mean_step_wall_seconds
max_step_wall_seconds
target_step_wall_seconds = 0.2
target_met
```

Grid fitting remains an explicit CPU setup step in this reduced diagnostic.
The per-step measurement/owner/reduction hot path is device-native.

## Remote Experiments

Default CPU route:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py
```

Result: PASS.

```text
phase_region_graph_steps_admitted = 1
steps                             = 8
max_amplitude_error               = 2.785727377941e-14
max_velocity_error                = 3.482433087558e-10
max_energy_drift                  = 8.356546623106e-10
max_residual_l2                   = 0.000000000000e+00
max_volume_drift                  = 2.710505431214e-20
max_step_wall_seconds             = 2.060934901237e-03
target_met                        = 1
force_admissible                  = 0
```

GPU route, 8 steps:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py ARGS='--use-gpu'
```

Result: PASS.

```text
phase_region_graph_steps_admitted = 1
steps                             = 8
max_amplitude_error               = 2.785727377941e-14
max_velocity_error                = 3.482433087558e-10
max_energy_drift                  = 8.356546623106e-10
max_residual_l2                   = 0.000000000000e+00
max_volume_drift                  = 5.421010862428e-20
max_step_wall_seconds             = 1.781878299080e-01
target_met                        = 1
force_admissible                  = 0
```

GPU route, 32 steps:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py ARGS='--use-gpu --steps 32'
```

Result: PASS.

```text
phase_region_graph_steps_admitted = 1
steps                             = 32
dt                                = 2.000000000000e-05
t_final                           = 6.400000000000e-04
t_over_T                          = 1.369189442149e-02
max_amplitude_error               = 4.452018994346e-13
max_velocity_error                = 1.392972602283e-09
max_energy_drift                  = 1.333958441357e-08
max_residual_l2                   = 0.000000000000e+00
max_volume_drift                  = 5.421010862428e-20
max_step_wall_seconds             = 3.885252121836e-02
target_met                        = 1
final_amplitude                   = 1.992603619994e-04
final_exact_amplitude             = 1.992603624446e-04
force_admissible                  = 0
```

The 8-step GPU path meets the `0.2 s/step` target even with startup effects in
the step loop.  The 32-step run measures the steady route more clearly at
`3.89e-02 s/step` maximum.

## Remote Tests

Command:

```text
make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py twophase/tests/test_phase_region_measure.py twophase/tests/test_phase_owner_map.py -q'
```

Result: PASS.  The current remote make target ran the suite under its
configured root:

```text
871 passed, 35 skipped
```

Local targeted validation also passed:

```text
24 passed, 3 skipped
```

## Boundary

This is a GPU optimization for the reduced graph-chart PhaseRegion few-step
experiment.  It does not connect the PhaseRegion force cochain to the production
Navier--Stokes runtime, does not expose nodal `force_components`, and does not
advance T/8.

`force_admissible=0` remains correct.  The known production boundary remains
the graph/closed face-force consumer and runtime state-update gate.

[SOLID-X] Backend-aware graph measurement, phase-owner map, PhaseRegion
measurement, tests, experiment metrics, artifact/wiki/ledger only; no solver
algorithm, YAML physical parameter, CFL, damping, smoothing, tolerance
weakening, rebuild skipping, FD/WENO/PPE fallback, hidden CPU fallback,
production graph/closed PhaseRegion face-force route, nodal
`force_components` route, T/8 runtime run, main merge, branch deletion,
worktree removal, or origin push changed.
