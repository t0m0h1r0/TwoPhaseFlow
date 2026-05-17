# CHK-RA-CH14-VAR-030 - PhaseRegion runtime dry-run adapter

Date: 2026-05-17

Scope: add and validate a Ch14 PhaseRegion runtime dry-run adapter for the
oscillating-droplet initial snapshot.  This checkpoint does not advance a time
step, assemble force, project pressure/velocity, run nonlinear optimization,
micro-step, or run T/8.

## Motivation

The previous checkpoint made the owner map explicit:

```text
runtime q_l = |Omega_l cap C|
PhaseRegion q_g = |C| - q_l
```

The next gate was to prove that the runtime snapshot can be consumed by
PhaseRegion diagnostics without silently mixing liquid and gas ownership or
rebuilding `phi`.

## Implementation

Added:

```text
experiment/ch14/diagnose_phase_region_runtime_dry_run_adapter.py
```

The script:

1. reads `experiment/ch14/config/ch14_oscillating_droplet.yaml`;
2. builds the initial `GeometricPhaseState` on the configured admission grid;
3. reads runtime liquid cell volume `q_l = GeometricPhaseState.q`;
4. maps it to gas owner with `map_cell_measure_to_phase_owner`;
5. projects the liquid snapshot to a closed radial chart only as an admitted
   interface diagnostic;
6. reinterprets the same closed boundary as a `GAS_OUTSIDE` PhaseRegion
   component;
7. assembles gas residual
   `r_g = q_target,g - Q_h(Omega_g)` through
   `assemble_phase_region_measurement`;
8. saves `q_l`, owner `q_g`, PhaseRegion `q_g`, residual, and boundary
   visualization.

The dry-run records:

```text
source_phase = LIQUID
owner_phase = GAS
complement_used = true
phase_role = GAS_OUTSIDE
attachment = NONE
runtime_steps = 0
force_admissible = false
```

## Equation -> Discretization -> Code

| Equation | Discretization | Code |
|---|---|---|
| Runtime owner `q_l = |Omega_l cap C|` | `GeometricPhaseState.q` on the YAML admission grid | `_phase_state_on_admission_grid` |
| PhaseRegion owner `q_g = |C| - q_l` | exact cellwise finite-volume complement | `map_cell_measure_to_phase_owner` |
| Closed interface chart | one closed radial F0 diagnostic from runtime `q_l` | `project_closed_radial_mode_f0` |
| Gas outside PhaseRegion | single `CLOSED_RADIAL` component with `PhaseRole.GAS_OUTSIDE` | `_region_from_closed_gas_outside` |
| Residual split | `r_g = q_target,g - q_phys,g` | `assemble_phase_region_measurement` |

## Validation Result

Remote command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_dry_run_adapter.py
```

Result: PASS.

```text
complement_used      = 1.0
gas_target_volume    = 3.224248620783e-04
gas_physical_volume  = 3.225975459493e-04
residual_l2          = 1.022474608009e-07
residual_volume_abs  = 1.726838710861e-07
perimeter            = 3.145493799546e-02
force_admissible     = 0.0
```

Local outputs pulled from remote:

```text
experiment/ch14/results/diagnose_phase_region_runtime_dry_run_adapter/data.npz
experiment/ch14/results/diagnose_phase_region_runtime_dry_run_adapter/phase_region_runtime_dry_run_adapter.pdf
```

The PDF is nonempty (`93K`) and visualizes runtime `q_l`, owner `q_g`,
PhaseRegion `q_g`, and `r_g`.

## Code Review

[SOLID-X] no violation.  The new code is an experiment diagnostic using
`twophase.tools.experiment` for I/O/plotting.  No `src/twophase/` production
runtime adapter, YAML route, solver, pressure/velocity projection, capillary
force path, nonlinear optimizer, GPU path, smoothing, damping, CFL retuning,
or tolerance weakening was added.

## Theory Consistency

This dry-run removes the implicit owner mismatch for the first runtime-facing
PhaseRegion diagnostic.  It still does not authorize force coupling or
micro-stepping because the force oracle and pressure/velocity work pairing
remain unproven.

The accepted state after this checkpoint is:

```text
runtime q_l is visible
owner q_g is visible
PhaseRegion q_phys,g is visible
r_g is visible
perimeter is visible
force_admissible = false
```

## Final Validation

```text
git diff --check = PASS
docs/wiki WIKI count = 423
docs/wiki/experiment WIKI-E count = 72
targeted CHK/wiki/script scan = PASS
```

The local `.venv/bin/python3` path is not present in this worktree, so local
`py_compile` was not used; the remote `make cycle` execution validated the
script syntax and runtime path.
