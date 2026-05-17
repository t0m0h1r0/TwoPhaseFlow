# WIKI-L-074 - Ch14 PhaseRegion Graph GPU Hot Path PASS

## Claim

The reduced Ch14 PhaseRegion capillary-wave graph route has a GPU hot path that
meets the `0.2 s/step` target without changing the underlying route.

## Contract

Use the optimized path only for the reduced graph-chart experiment:

```text
eta -> q_l = Q_h(eta)
q_g = |C| - q_l
PhaseRegionBatch(GAS_ABOVE graph)
assemble_phase_region_measurement(...)
```

The graph `Q_h` fast path is:

```text
graph_q_from_eta_column_integral(grid, eta_nodes)
```

It computes exact P1 graph cell measures by vectorized column integration on
`backend.xp`.  `map_cell_measure_to_phase_owner(...)` and
`assemble_phase_region_measurement(...)` preserve device arrays through the
owner-map and measurement reductions; host conversion is limited to explicit
scalar diagnostics and plotting snapshots.

## Evidence

Artifact:

```text
artifacts/A/ch14_phase_region_graph_gpu_hot_path_CHK-RA-CH14-VAR-055.md
```

Remote validation:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py
= PASS: CPU/default route, max_step_wall_seconds=2.060934901237e-03

make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py ARGS='--use-gpu'
= PASS: GPU 8 steps, max_step_wall_seconds=1.781878299080e-01, target_met=1

make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py ARGS='--use-gpu --steps 32'
= PASS: GPU 32 steps, max_step_wall_seconds=3.885252121836e-02, target_met=1

make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py twophase/tests/test_phase_region_measure.py twophase/tests/test_phase_owner_map.py -q'
= PASS: 871 passed, 35 skipped
```

The GPU run preserves the exact-reference checks:

```text
max_amplitude_error = 4.452018994346e-13
max_velocity_error  = 1.392972602283e-09
max_energy_drift    = 1.333958441357e-08
max_residual_l2     = 0
max_volume_drift    = 5.421010862428e-20
```

## Boundary

This is not a production Navier--Stokes runtime coupling.  The reduced graph
route still reports `force_admissible=0`; face-force consumption, runtime
velocity reconstruction/update, closed-chart GPU hot path, and T/8 execution
remain separate gates.
