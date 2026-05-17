# CHK-RA-CH14-VAR-018 - PhaseRegion InterfaceAtlas schema module

Date: 2026-05-17

Scope: Module A implementation.  This checkpoint adds schema and validation
only.  It does not add `Q_h`, perimeter reductions, force coupling, pressure or
velocity projection, runtime adapters, experiment YAML, T/8 runs, tolerance
weakening, smoothing, damping, CFL retuning, rebuild skipping, FD/WENO/PPE
fallback, or hidden CPU fallback.

## Implemented files

- `src/twophase/geometry/interface_atlas.py`
- `src/twophase/geometry/__init__.py`
- `src/twophase/tests/test_phase_region_atlas.py`

## Equation -> Discretization -> Code

| Equation object | Discretization | Code |
|---|---|---|
| `Omega_g` | finite-dimensional phase-region state `R_h` | `PhaseRegionBatch` |
| `Gamma = boundary Omega_g` | packed atlas components | `InterfaceAtlas` |
| chart stratum `tau` | chart/topology/attachment/orientation/phase/constraint labels | `ChartType`, `TopologyType`, `BoundaryAttachment`, `PhaseRole`, `ConstraintPolicy` |
| packed vectorization | component-major offsets by batch and by component payload | `component_offsets`, `dof_offsets`, `vertex_offsets`, `active_cell_offsets` |
| future `Q_h(R_h)` | active-band cells and weights | `active_cell_ids`, `active_weights` |

## Coding result

The module introduces:

- enum labels for chart type, topology, boundary attachment, phase role, and
  constraint policy;
- immutable `InterfaceAtlas` metadata;
- immutable `PhaseRegionBatch` packed payload;
- fail-closed validators for:
  - positive batch size;
  - batch-packed component order;
  - monotone offsets;
  - integer-valued labels and offsets;
  - unit orientation signs;
  - closed components with no boundary attachment;
  - closed-radial charts only on closed topology;
  - graph/open components with graph/open gas-side phase roles;
  - payload lengths matching offsets;
  - finite dofs, vertices, and active weights.

The helper `component_offsets_from_batch_ids` builds offsets from sorted
component ids, preserving the packed-by-batch invariant required for later
vectorized segment reductions.

## Code review

Review finding fixed before acceptance:

- Initial integer validation used direct integer conversion, which could
  silently truncate non-integer labels or offsets.  The validator now checks
  finite integer-valued input before casting.

No C1/SOLID issue found: the new module performs schema validation only and has
no I/O, runtime config dependency, plotting, transport, force, or pressure
responsibility.

## Theory consistency

This module implements only the owner stratum:

```text
R_h = PhaseRegionBatch(InterfaceAtlas, packed dofs, vertices, active cells)
```

It deliberately does not construct:

```text
q_phys = Q_h(R_h)
r = q_T - q_phys
E_h = sigma sum perimeter(component)
T_h or T_h^*
```

Therefore it preserves the VAR-017 gate: the next implementation step is still
the closed bubble + top layer atlas smoke oracle, not force coupling or T/8.

## Tests

Command:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_atlas.py -q'
```

The project make target ran the remote suite and passed:

```text
809 passed, 35 skipped
```

Targeted checks in `test_phase_region_atlas.py` cover:

- closed-bubble + top-layer schema acceptance;
- packed slices for dofs, vertices, active cell ids, and weights;
- component grouping by chart type;
- sorted component offset construction;
- fail-closed non-integer component ids;
- rejection of closed component boundary attachment;
- rejection of payload length mismatch;
- rejection of non-unit orientation and invalid vertex shape.

