# CHK-RA-CH14-AO-FASTVOL-050 — Ch14 Capillary Fitted-Grid Stratum Guard

## Request

Use the theory-first RCA/countermeasure policy to resolve the current Chapter 14 capillary-wave failure without symptom-only tricks.

## Contract

SP-AO P1 cut geometry assumes a regular fixed sign stratum:

- no grid node may lie on `phi = 0`;
- `Q_h(phi)` and `S_h(phi)` are differentiated only inside that open stratum;
- `J_q J_q^T` must not contain near-zero active rows created by a vertex-touching interface.

Interface-fitted grid rebuilds therefore must refine near the interface without placing the tracked interface on tensor-product nodes.

## Falsification Summary

Runner-equivalent initial fitted-grid rebuild reproduced the failure while the no-rebuild control stayed small.

Before the fix, with `--runner-initial-grid-rebuild`:

- `q - Q_h(phi)` compatibility: `0.0`
- Young-Laplace normal residual: `3.269e-13`
- `sign_margin`: `1.735e-18`
- `row_norm_min`: `1.966e-34`
- capillary weighted acceleration: `1.745e10`
- `u_star`: `1.044e3`
- `ppe_rhs`: `3.732e7`

This falsifies PCG convergence and q/phi compatibility as root causes. The violated contract is the P1 fixed-stratum regularity of the rebuilt nonuniform grid.

## Fix

`Grid.update_from_levelset` now enforces the regular P1 stratum after interface-fitted coordinate construction:

- keep the old metric epoch coordinates;
- interpolate the level set onto the rebuilt tensor grid;
- find nodes with `|phi|` below a metric-scale stratum floor;
- move the offending coordinate line along the strongest local level-set gradient;
- preserve monotonicity and the configured cell-width floor;
- rebuild metrics only after the corrected coordinates are installed.

This is not an arbitrary micro-offset. It is a coordinate-generation admissibility condition required by the differentiability domain of `Q_h` and `S_h`.

The capillary YAML also no longer asks the plotter to relabel a nonintegrable pressure-reaction face cochain as scalar `pressure_hodge`; it plots the stored scalar pressure only as a gauge diagnostic.

## Validation

- `python3 -m py_compile src/twophase/core/grid.py src/twophase/tests/test_grid.py experiment/ch14/diagnose_ao_stage_chain.py` PASS.
- Remote full suite after the grid/test change: `738 passed, 33 skipped`.
- Remote targeted after the YAML change:
  - `-k update_from_levelset_keeps_wave_nodes` PASS.
  - `-k ch14_capillary_yaml_loads_execution_stack` PASS.
- Remote runner-equivalent stage chain, 3 steps with initial fitted-grid rebuild:
  - step 1 `sign_margin=2.654e-05`, `row_norm_min=3.066e-08`, capillary weighted acceleration `2.626`, `u_star=3.507e-07`, `ppe_rhs=7.225e-04`;
  - no fail-close over 3 steps.
- Remote production runner shortened to `--final-time 0.000171430986` PASS:
  - saved 10 time samples through `t=1.71430986e-04`;
  - final kinetic energy `8.630e-16`;
  - volume conservation drift `0.0`;
  - plots generated successfully after the YAML output fix.
- Full 1/4-period production run was attempted and stopped manually after 16m34s because the current Python-level AO path was too slow for an interactive turn; it did not reach a fail-close before termination.

## SOLID

- [SOLID-S] Grid rebuild owns coordinate admissibility; AO geometry still owns cut-cell derivatives and compatibility.
- [SOLID-O] The guard extends nonuniform coordinate generation without changing uniform-grid behavior or solver APIs.
- [SOLID-D] The guard depends on level-set and metric contracts, not on capillary/PPE concrete implementations.
- [SOLID-X] No physical parameters, CFL, damping, smoothing, tolerance weakening, FD/WENO/PPE fallback, dense CPU fallback, hidden PCG/DC fallback, arbitrary `1e-10` coordinate nudge, main merge, or branch deletion introduced.
