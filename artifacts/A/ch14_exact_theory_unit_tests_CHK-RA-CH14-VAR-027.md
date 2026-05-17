# CHK-RA-CH14-VAR-027 - Exact theory unit tests

Date: 2026-05-17

Scope: strengthen Ch14 PhaseRegion/q-manifold unit tests so they compare
against exact or closed-form theoretical quantities, not only oracle trend
metrics.  This checkpoint changes tests only.  It does not add production
runtime adapters, YAML routes, force coupling, pressure/velocity projection,
nonlinear optimization, long stepping, or T/8.

## Motivation

The user asked that tests also verify whether the implementation is
theory-consistent and correct, including comparison with exact solutions.  The
existing tests already checked residual splitting, finite-difference
covectors, and remote oracle PASS metrics, but several acceptance points were
still mostly behavioral.

This checkpoint adds exact theoretical references where they are available.

## Added Exact Checks

| Theory object | Exact reference | Test |
|---|---|---|
| Constant graph chart `Gamma_h={y=h}` | `q_{ij}=dx_i clamp(h-y_j,0,dy_j)` on a fitted nonuniform grid | `test_graph_constant_chart_matches_exact_cell_volumes_on_fitted_grid` |
| Graph F0 constant mode | exact mean height `h` and zero residual | same test |
| Regular closed polygon | `A=(M/2)R^2 sin(2pi/M)`, `L=2MR sin(pi/M)` | `test_closed_regular_polygon_matches_exact_geometry_and_radial_variations` |
| Polygon first variations under uniform radial expansion | `dA/dR=2A/R`, `dL/dR=L/R` | same test |
| F1 low-mode KKT | explicit weighted, regularized, constrained KKT matrix solve | `test_low_mode_kkt_matches_exact_weighted_regularized_constrained_system` |
| Gas owner complement | exact algebraic map `q_g=cell_area-q_l` under `PhaseRole.GAS_OUTSIDE` | `test_gas_owner_measurement_matches_exact_liquid_complement` |

## Theory Consistency

The tests keep the current ownership ladder:

```text
Gamma_h or PhaseRegionBatch owns the admitted state
Q_h(owner) produces q_phys
r = q_T - q_phys remains diagnostic
force_admissible = false
```

The new gas-complement test is especially important before runtime dry-run
work.  It does not implement the adapter; it fixes the algebraic expectation
that a runtime liquid volume can only enter a gas-owned PhaseRegion through an
explicit complement map.

## Code Review

[SOLID-X] no violation.  The patch touches only unit tests:

- `src/twophase/tests/test_q_manifold_projection.py`
- `src/twophase/tests/test_phase_region_admission.py`
- `src/twophase/tests/test_phase_region_measure.py`

No helper module, runtime path, plotting path, experiment YAML, production
solver, GPU route, capillary force route, pressure/velocity coupling, or
nonlinear optimizer was modified.

## Validation

First remote run found one test-harness bug, not a theory or implementation
failure:

```text
np.block rejects tuple block layout
```

The test was corrected to use list block layout.  Final remote validation:

```text
make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py twophase/tests/test_phase_region_admission.py twophase/tests/test_phase_region_measure.py -q'
```

Result:

```text
825 passed, 35 skipped
```

Formatting and wiki validation:

```text
git diff --check = PASS
docs/wiki WIKI count = 420
docs/wiki/code WIKI-L count = 57
targeted CHK/wiki/test scan = PASS
```
