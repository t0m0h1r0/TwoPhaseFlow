# CHK-RA-CH14-VAR-022 - PhaseRegion boundary/nonuniform audit

Date: 2026-05-17

Scope: audit and hardening after the question: "境界・非一様格子についても
大丈夫か？ 他にも怪しいところがあったらチェックして".  This checkpoint
does not add force coupling, pressure/velocity projection, production runtime
adapters, F0/F1 chart admission, nonlinear optimization, YAML routes, or T/8.

## Findings

| ID | Severity | Finding | Action |
|---|---|---|---|
| A1 | High | Graph/open atlas components could omit boundary attachment, despite boundary ownership being part of the theory. | Added fail-closed validation requiring graph/open components to declare a boundary attachment. |
| A2 | High | `component_q` could contain negative entries or exceed cell capacity and still be reduced if the final `q_phys` looked admissible. | Added component-level nonnegative and capacity checks. |
| A3 | Medium | Singular low-mode KKT systems escaped as raw NumPy `LinAlgError`; indefinite energy Hessians were not rejected. | Converted singular systems to `AtlasValidationError` and require symmetric positive-semidefinite Hessians. |
| A4 | Medium | The PhaseRegion atlas smoke oracle only validated `alpha_grid=1.0`. | Added `--alpha-grid`; reran the smoke oracle with `alpha_grid=2.0`. |
| A5 | Residual risk | Existing graph F0 mode projection still requires a uniform periodic x-grid. | Kept as a blocked gate for future chart-specific nonuniform F0/F1 admission. |

## Code changes

- `src/twophase/geometry/interface_atlas.py`
  - graph/open components now fail closed if `BoundaryAttachment.NONE`.
- `src/twophase/geometry/phase_region_measure.py`
  - component q now fails closed if below zero beyond tolerance;
  - component q now fails closed if it exceeds `cell_area` beyond tolerance.
- `src/twophase/geometry/phase_region_admission.py`
  - singular KKT systems now raise `AtlasValidationError`;
  - energy Hessians must be symmetric positive semidefinite.
- `experiment/ch14/diagnose_phase_region_atlas_smoke_oracle.py`
  - added `--alpha-grid`;
  - recorded `alpha_grid` in summaries and the plot text box.
- Tests were extended in:
  - `src/twophase/tests/test_phase_region_atlas.py`;
  - `src/twophase/tests/test_phase_region_measure.py`;
  - `src/twophase/tests/test_phase_region_admission.py`.

## Theory consistency

The hardening keeps the PhaseRegion contract intact:

```text
R_h owns topology, attachment, orientation, phase role, constraints
component q must be physical cell measure
q_phys and r are diagnostics
F1 KKT remains a low-mode correction only
force_admissible remains false
```

The audit does not make the graph F0 path nonuniform-ready.  The known
remaining blocker is:

```text
project_column_height_to_graph currently requires uniform x spacing
```

Nonuniform atlas smoke is now validated for direct chart measurement and
component reduction, but nonuniform F0/F1 admission still needs a separate
chart-specific implementation.

## Validation

Remote suite command:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_atlas.py twophase/tests/test_phase_region_measure.py twophase/tests/test_phase_region_admission.py -q'
```

Result:

```text
818 passed, 35 skipped
```

Uniform smoke command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_atlas_smoke_oracle.py
```

Result: PASS with:

- `alpha_grid = 1.000000000000e+00`;
- `residual_l2 = 1.321657093465e-06`;
- `force_admissible = 0.0`.

Nonuniform smoke command:

```text
make run EXP=experiment/ch14/diagnose_phase_region_atlas_smoke_oracle.py ARGS='--alpha-grid 2.0'
make pull
```

Result: PASS with:

- `alpha_grid = 2.000000000000e+00`;
- `total_volume = target_volume = 2.652951873059e-01`;
- `residual_volume_abs = 1.058791184068e-22`;
- `residual_l2 = 1.321657093465e-06`;
- `bubble_fd_residual = 1.828148743499e-11`;
- `layer_fd_residual = 1.110222637694e-09`;
- `force_admissible = 0.0`.

Formatting:

```text
git diff --check
```

Result: PASS.

Local NPZ inspection with bare `python3` failed because the local interpreter
lacks NumPy; the remote run output above is the validation evidence.

