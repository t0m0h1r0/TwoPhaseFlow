# CHK-RA-CH14-VAR-019 - PhaseRegion atlas smoke oracle

Date: 2026-05-17

Scope: Module B implementation.  This checkpoint adds a synthetic experiment
oracle for a closed bubble plus top air layer.  It does not add runtime force
coupling, pressure/velocity projection, nonlinear optimization, production
YAML, or T/8.

## Implemented files

- `experiment/ch14/diagnose_phase_region_atlas_smoke_oracle.py`

Generated, untracked result files:

- `experiment/ch14/results/diagnose_phase_region_atlas_smoke_oracle/data.npz`
- `experiment/ch14/results/diagnose_phase_region_atlas_smoke_oracle/phase_region_atlas_smoke_oracle.pdf`

## Equation -> Discretization -> Code

| Equation object | Discretization | Code |
|---|---|---|
| `Omega_g = Omega_bubble union Omega_layer` | one `PhaseRegionBatch` with two components | `_build_region` |
| `Gamma = Gamma_bubble union Gamma_layer` | closed radial chart + graph chart | `closed_radial_chart_from_modes`, `_top_layer_eta` |
| `q_phys = Q_h(Omega_g)` | component measures summed cellwise | `q_bubble + q_layer` |
| `E = sigma (L_bubble + L_layer)` | polygon perimeter + graph segment length | `closed_polygon_geometry`, `graph_segment_energy_gradient` |
| transported measure split | synthetic `q_T = q_phys + r` with total-volume-neutral residual | `_zero_total_cell_residual` |
| force gate | blocked | `force_admissible = 0.0` |

## Coding result

The oracle builds:

```text
component 0: CLOSED_RADIAL, CLOSED, no attachment, GAS_INSIDE
component 1: GRAPH, GRAPH_PERIODIC, TOP attachment, GAS_ABOVE
```

It packs the two components into `PhaseRegionBatch`, computes component q
measures, sums `q_phys`, adds a bounded total-volume-neutral synthetic
residual, and visualizes:

- bubble component;
- top-layer component;
- `q_phys`;
- synthetic `q_T`;
- `r / cell area`;
- component overlays and scalar diagnostics.

## Code review

Review findings fixed before acceptance:

- Active payload initially collected only positive entries, which dropped tiny
  signed roundoff from the top-layer component and failed the component-sum
  check.  It now preserves all nonzero contributions.
- The first residual mask included nearly saturated/empty cells, forcing an
  almost invisible residual.  The residual source now uses only intermediate
  cut cells so the diagnostic is visible without changing the force gate.

No C1/SOLID issue found: the script is an experiment oracle that uses
`twophase.tools.experiment` for I/O/plotting; no I/O enters `src/twophase/`.

## Theory consistency

The oracle exercises the PhaseRegion-primary theory:

```text
R_h -> q_phys, component perimeters, declared labels, residual diagnostics
```

It does not treat `q_T` as exact geometry.  The synthetic residual remains in
`r`, and `force_admissible` is explicitly zero.

The chart split is not a theory split:

```text
closed bubble chart + graph top-layer chart
same Omega_g owner
same perimeter-sum energy
same total gas measure
```

## Validation

Command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_atlas_smoke_oracle.py
```

Result: PASS.  Key metrics:

- `bubble_volume = 4.529518730590e-02`;
- `layer_volume = 2.200000000000e-01`;
- `total_volume = 2.652951873059e-01`;
- `target_volume = 2.652951873059e-01`;
- `residual_volume_abs = 1.058791184068e-22`;
- `residual_l2 = 1.321657093465e-06`;
- `bubble_length = 7.581754487119e-01`;
- `layer_length = 1.015587078123e+00`;
- `total_perimeter = 1.773762526835e+00`;
- `bubble_fd_residual = 1.828148743499e-11`;
- `layer_fd_residual = 1.110222637694e-09`;
- `force_admissible = 0.0`.

The output PDF is:

```text
experiment/ch14/results/diagnose_phase_region_atlas_smoke_oracle/phase_region_atlas_smoke_oracle.pdf
```

