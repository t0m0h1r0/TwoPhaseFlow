# CHK-RA-CH14-VAR-029 - Phase-owner map implementation

Date: 2026-05-17

Scope: implement the explicit finite-volume phase-owner map required before a
PhaseRegion runtime dry-run adapter.  This checkpoint does not add a runtime
adapter, force coupling, pressure/velocity coupling, nonlinear optimization,
micro-stepping, or T/8.

## Motivation

`WIKI-E-071` identified the next blocker:

```text
GeometricPhaseState.q = liquid cell volume q_l
PhaseRegionBatch theory = gas-region owner Omega_g
```

The runtime dry-run must not silently feed liquid `q_l` into a gas-owned
PhaseRegion measurement.  The owner conversion has to be visible and tested.

## Implementation

Added `src/twophase/geometry/phase_owner_map.py`:

- `CellMeasurePhase`: explicit `LIQUID` / `GAS` finite-volume owner label;
- `PhaseOwnerMapResult`: converted measure plus source/owner labels,
  `complement_used`, volumes, and capacity diagnostics;
- `map_cell_measure_to_phase_owner`: validates shape, finite positive
  `cell_area`, finite bounded source q, finite nonnegative tolerance, then
  returns either the pass-through measure or the exact complement.

The only admitted cross-phase map is:

```text
q_owner = |C| - q_source, source_phase != owner_phase
```

No clipping is performed; capacity violations fail closed.

## Equation -> Discretization -> Code

| Equation | Discretization | Code |
|---|---|---|
| `Omega_l` and `Omega_g` partition each finite-volume cell | `q_l + q_g = |C|` cellwise | `map_cell_measure_to_phase_owner` complement branch |
| runtime owns liquid `q_l` | `q_source` declared with `CellMeasurePhase.LIQUID` | `source_phase` argument and result field |
| PhaseRegion currently owns gas `Omega_g` | target `q_g` declared with `CellMeasurePhase.GAS` | `owner_phase` argument and result field |
| no implicit owner mixing | visible `complement_used` plus source/owner volumes | `PhaseOwnerMapResult` |

## Tests

Added `src/twophase/tests/test_phase_owner_map.py`:

- exact liquid-to-gas complement on nonuniform cell capacities;
- gas-to-gas pass-through without hidden complement;
- fail-closed shape, negative q, over-capacity q, invalid phase, and invalid
  tolerance checks.

Updated `test_phase_region_measure.py` so the existing gas-owner complement
measurement test now uses `map_cell_measure_to_phase_owner` before
`assemble_phase_region_measurement`.

## Code Review

[SOLID-X] no violation.  The new module is a pure algebraic geometry-layer
helper with no I/O, config dependency, plotting, runtime advancement,
pressure/velocity projection, force path, or solver responsibility.  Existing
measurement reduction remains separate; the owner map only prepares the cell
measure owner consumed by that reduction.

## Theory Consistency

The implemented owner chain is:

```text
runtime q_l = |Omega_l cap C|
q_g = |C| - q_l
PhaseRegion q_target = q_g
r_g = q_target,g - Q_h(Omega_g)
force_admissible = false
```

This removes the implicit liquid/gas owner mismatch, but it still does not
authorize force coupling or T/8.  The next runtime dry-run must record the
owner map, pre/post q, component volumes, residual, perimeter, attachment, and
`force_admissible=false`.

## Validation

Remote test:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_owner_map.py twophase/tests/test_phase_region_measure.py -q'
```

Result:

```text
829 passed, 35 skipped
```

Formatting and wiki validation:

```text
git diff --check = PASS
docs/wiki WIKI count = 422
docs/wiki/code WIKI-L count = 59
targeted CHK/wiki/test scan = PASS
```
