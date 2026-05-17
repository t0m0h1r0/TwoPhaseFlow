---
ref_id: WIKI-L-075
title: "Ch14 Capillary YAML Output Contract and Snapshot Plotter PASS"
domain: code
status: ACTIVE
tags: [ch14, yaml, output_contract, snapshots, plotting, phase_region, capillary]
sources:
  - path: experiment/ch14/diagnose_phase_region_capillary_graph_steps.py
    description: "YAML-owned reduced PhaseRegion graph run and snapshot writer"
  - path: src/twophase/tools/plot_snapshot_figures.py
    description: "YAML snapshot-series renderer for phi, velocity, and pressure"
  - path: src/twophase/tests/test_config_io_fccd.py
    description: "Canonical Ch14 YAML tests"
  - path: artifacts/A/ch14_capillary_yaml_time_owned_outputs_CHK-RA-CH14-VAR-063.md
    description: "Validation artifact for output timing and figures"
depends_on:
  - "[[WIKI-L-074]]"
  - "[[WIKI-X-057]]"
  - "[[WIKI-E-085]]"
consumers:
  - domain: code
    usage: "Use before editing Ch14 capillary config loading, snapshot data, or plot fields"
  - domain: experiment
    usage: "Use before rerunning plot-only or regenerating Chapter 14 figures"
  - domain: paper
    usage: "Use before accepting figure replacements"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Capillary YAML Output Contract and Snapshot Plotter PASS

## Claim

The Ch14 capillary reduced graph route now treats the canonical YAML as the
owner of the route and output contract.  The code must not infer a different
route by script defaults when the YAML is present.

## Equation to Discretization to Code

| Layer | Contract |
|---|---|
| Equation | `R_h` owns the phase region, `q=Q_h(R_h)` is a measure, `phi` is a graph gauge. |
| Discretization | The graph chart uses exact P1 column integration and physical-time snapshot selection. |
| Code | `graph_q_from_eta_column_integral`, `PhaseRegionBatch`, `map_cell_measure_to_phase_owner`, and `assemble_phase_region_measurement` assemble the measure route. |
| Code | `diagnose_phase_region_capillary_graph_steps.py` derives steps from YAML `cfl=1.0`, maps snapshot times to nearest steps, and saves `phi/u/v/pressure/rho` snapshots. |
| Code | `plot_snapshot_figures.py` renders YAML `snapshot_series` for `phi`, velocity, and pressure with shared axis ticks/limits. |

## Implementation Contract

The experiment script must:

- merge canonical YAML sections over the retained legacy-compatible base
  schema;
- derive step count and `dt` from the capillary CFL, not from a YAML fixed
  `dt`;
- preserve `interface` and `numerics` as visible route declarations;
- store snapshots on comparable grids:

```text
phi_snapshots      = (nt, ny + 1, nx + 1)
u_snapshots        = (nt, ny + 1, nx + 1)
v_snapshots        = (nt, ny + 1, nx + 1)
pressure_snapshots = (nt, ny + 1, nx + 1)
q_l_snapshots      = (nt, ny, nx)
q_g_snapshots      = (nt, ny, nx)
```

The plotter must:

- accept `snapshot_series.field = phi`;
- render `phi`, velocity, and pressure from the cached NPZ in `--plot-only`;
- apply shared `x_ticks`/`y_ticks` when fields are compared;
- fail closed on missing fields rather than silently plotting stale data.

## Validation

Validation performed for this contract:

```text
py_compile diagnose_phase_region_capillary_graph_steps.py PASS
py_compile plot_snapshot_figures.py PASS
make test PYTEST_ARGS='-k ch14_capillary_yaml -q' PASS
make test PYTEST_ARGS='-k ch14_canonical_yamls_use_theory_cfl_not_fixed_dt -q' PASS
make test PYTEST_ARGS='-k plot_snapshot_figures -q' PASS
--plot-only with ch14_capillary.yaml PASS
```

## Failure Traps

Do not reintroduce:

- fixed YAML `dt` for this canonical capillary run;
- output specified only by step interval;
- `psi` snapshot figures where the paper contract requires `phi`;
- pressure/velocity plots with incompatible axes;
- hidden CPU fallback inside the GPU hot path;
- old data reuse after a route-defining YAML correction.
