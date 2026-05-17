# CHK-RA-CH14-VAR-020 - PhaseRegion measure reduction module

Date: 2026-05-17

Scope: Module C implementation.  This checkpoint adds component-measure
reductions for `PhaseRegionBatch`.  It does not construct chart gauges,
reconstruct `phi`, perform F0/F1 admission, build force coupling, project
pressure/velocity, add runtime adapters, or run T/8.

## Implemented files

- `src/twophase/geometry/phase_region_measure.py`
- `src/twophase/geometry/__init__.py`
- `src/twophase/tests/test_phase_region_measure.py`

## Equation -> Discretization -> Code

| Equation object | Discretization | Code |
|---|---|---|
| `R_h` | `PhaseRegionBatch` owner | input `region` |
| `Q_h(R_h)` | vectorized batch sum of measured component q arrays | `assemble_phase_region_measurement` |
| `E_h(R_h)` | vectorized batch sum of component perimeters | `batch_perimeters` |
| `q_T` | optional transported target measure | `q_target` |
| `r=q_T-Q_h(R_h)` | residual diagnostics only | `residual`, `residual_l2`, `residual_volume` |
| force gate | blocked | `force_admissible=False` |

## Coding result

The module introduces `PhaseRegionMeasurement` and
`assemble_phase_region_measurement`.  The implementation:

- accepts `component_q[n_components, *grid_shape]`;
- reduces component measures into `q_phys[batch_size, *grid_shape]` with
  `np.add.at` over `component_to_batch`;
- computes component and batch volumes;
- computes component and batch perimeters;
- optionally computes residual diagnostics against `q_target`;
- optionally checks cell capacity against `cell_area`;
- always returns `force_admissible=False`.

## Code review

No C1/SOLID issue found.  The module is pure numerical reduction logic inside
`src/twophase/geometry` and has no I/O, plotting, config dependency, runtime
adapter, force path, or pressure/velocity coupling.

The helper deliberately accepts already-measured component q arrays.  It does
not hide a `phi` rebuild or chart measurement inside a reduction API.

## Theory consistency

This module implements only:

```text
component Q_h values -> batch Q_h(R_h)
component perimeters -> E_h(R_h)
optional q_T -> r
```

It preserves PhaseRegion ownership because all reductions use
`region.atlas.component_to_batch`.  It does not promote `q_T` to geometry and
does not make residual `r` a force source.

## Tests

Command:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_measure.py -q'
```

The project make target ran the remote suite and passed:

```text
812 passed, 35 skipped
```

Targeted checks cover:

- multi-batch component q reduction;
- batch perimeter reduction;
- residual diagnostics;
- one-batch `q_target` without a batch axis;
- fail-closed component perimeter shape;
- fail-closed cell-capacity overflow;
- fail-closed target shape mismatch.

