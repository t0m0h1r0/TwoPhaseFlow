# CHK-RA-CH14-CAPILLARY-AO-DESIGN-001 - strict SP-AO/AO-Fast implementation design review

Date: 2026-05-12
Branch/worktree: `codex/ra-ch14-capillary-ao-run-20260512` at `.claude/worktrees/codex-ra-ch14-capillary-ao-run-20260512`

## Scope

User request: strictly examine the implementation and design before coding.
The design must follow SP-AO, preserve AO-Fast, and reject tactical fixes.

No production source was changed in this review.

## Governing Equation

The implementation target is not a nodal Young--Laplace residual gate.  It is
the face-space pressure-reaction split

```text
source_face    = r_sigma
R_p(q_T)       = active pressure range + component-volume reaction range
balanced_face  = r_sigma - Pi^{M_f}_{R_p(q_T)} r_sigma
```

For the actual predictor/PPE/corrector pipeline, the component reaction must be
removed before the pressure range solve:

```text
C_ij = <Z_A(B_i), Z_A(B_j)>_{M_f}
r_i  = <Z_A(B_i), Z_A(r_sigma)>_{M_f}
C mu = r

corrected_source = r_sigma - B mu
pressure_range   = L_A(corrected_source)
balanced_face    = corrected_source - pressure_range
```

The runtime predictor should receive `corrected_source`; the explicit pressure
reaction should receive `pressure_range`; the admission diagnostic should read
`balanced_face`.

## Existing Code Audit

### Reusable structure

`src/twophase/simulation/ns_step_services.py` already has the correct downstream
three-stage shape:

1. add AO predictor increment to face-native predictor faces;
2. subtract AO pressure-reaction divergence from the PPE RHS;
3. add AO pressure-reaction faces to the corrector faces.

That structure is compatible with the theory if, and only if, the application
packet fields are reinterpreted as:

```text
predictor_face_acceleration         = M_f^{-1} corrected_source
pressure_reaction_face_acceleration = M_f^{-1} pressure_range
pressure_balanced_face_increment    = dt M_f^{-1} balanced_face
```

The current `GeometricRuntimeCapillaryApplicationState` can mostly carry this
pair, but its norm calculations currently use `capillary.material.face_hodge`.
That is unsafe once the split is performed on the NS projection face lattice.

### Current hard error

`src/twophase/simulation/geometric_phase_runtime_gpu.py` still constructs

```text
capillary_face = T_q^T pressure_cell
pressure_face  = capillary_face
residual_face  = 0
```

This must not be patched by changing only the classifier.  The source object
itself is wrong: the capillary source must be the bundle virtual-work covector,
not the pressure multiplier pulled back to faces.

### CPU helpers

`geometric_capillary_riesz_2d` already computes the CPU oracle `r_sigma` on the
geometric AO face complex.  `geometric_component_volume_reaction_hodge_2d`
removes component reactions, but it does not include the active PPE pressure
range and is therefore a diagnostic only, not the production `R_p(q_T)`.

`capillary_external_component_saddle_projection` is the closest existing
implementation to the required pressure-reaction theorem.  It computes
`Z_A(c)`, builds the small component saddle system from projected Hodge
residuals, returns `corrected_jump_components`, and exposes contract residuals.
It belongs in the simulation layer because it depends on `div_op`, `ppe_solver`,
and active pressure-flux kwargs.  It must not move into `geometry/`.

### AO-Fast infrastructure

`ActiveGeometryTable` and `ActiveSchurOperator` already provide compact
active-row `J`, `J^T`, and Schur matvecs.  They do not yet provide the final
active face-space pressure projection `L_A(c)` or a component saddle projection
on compact projection faces.  Until those exist, GPU production must fail
closed.

## Critical Design Gate: Face-Space Bridge

The current bridge `_geometric_to_projection_face_pair_2d` maps AO cell-face
increments to the NS projection face lattice by midpoint interpolation.  This
is acceptable only as a candidate bridge.  It is not automatically a
virtual-work-preserving covector transfer.

The split must not be computed on geometric faces and then interpolated after
the fact.  The strict order is:

```text
geometric r_sigma
  -> admitted projection-face covector/acceleration transfer
  -> L_A/Z_A/component saddle in the same projection M_f
  -> predictor/PPE/corrector packet
```

Required bridge proof:

```text
<r_sigma^P, w_P> = <r_sigma^G, Pi_GP w_P>
```

or an explicitly declared equivalent acceleration contract

```text
a_sigma^P = Pi_CF(M_G^{-1} r_sigma^G),
r_sigma^P = M_P a_sigma^P,
```

with a test showing that the pressure-adjoint metric used by
`capillary_pressure_adjoint_face_weights` is the metric used by the split.

If this bridge proof is absent, any nonzero capillary wave result is only a
numerical artifact and must be rejected.

## Proposed Module Boundary

Add a small simulation-layer service, not a geometry-layer service:

```text
src/twophase/simulation/geometric_capillary_reaction_split.py
```

Single responsibility: build a pressure-reaction split for one already
materialised AO capillary source and one active PPE/projection contract.

Suggested public dataclass:

```text
GeometricCapillaryReactionSplit
  raw_source_face_covectors
  projection_source_face_covectors
  component_reaction_face_covectors
  component_coefficients
  corrected_source_face_covectors
  pressure_range_face_covectors
  balanced_face_covectors
  face_weight_components
  source_weighted_l2
  corrected_source_weighted_l2
  pressure_range_weighted_l2
  balanced_weighted_l2
  max_abs_balanced_face_covector
  pressure_adjoint_residual
  saddle_constraint_linf
  bridge_work_residual_linf
  status
```

Suggested functions:

```text
build_geometric_capillary_reaction_split_cpu(...)
classify_geometric_capillary_reaction_split(...)
runtime_capillary_state_from_split(...)
```

GPU functions should exist only when they can keep the projection and reductions
device-resident:

```text
build_geometric_capillary_reaction_split_gpu(...)
```

Until that is true, the GPU entry must raise a fail-close error with a status
such as `gpu_active_pressure_reaction_projection_missing`.

## Runtime Data Model Changes

Do not only alter `_classify_capillary_pressure_range`.

Required state changes:

1. Add split-owned face weights to the runtime capillary/application state.
   Weighted norms must use the projection metric `M_f` returned by the active
   pressure-adjoint contract, not necessarily `material.face_hodge.weights`.

2. Preserve raw source diagnostics separately from predictor source:

   ```text
   raw_source_face_covectors
   corrected_source_face_covectors
   pressure_range_face_covectors
   balanced_face_covectors
   ```

3. Keep backward field names only as compatibility aliases if needed:

   ```text
   capillary_force_face_covectors      -> corrected_source_face_covectors
   pressure_reaction_face_covectors    -> pressure_range_face_covectors
   residual_face_covectors             -> balanced_face_covectors
   ```

4. Define admission exclusively by split metrics:

   ```text
   pressure_exact_static =
       split.balanced_weighted_l2 <= tolerance
       and split.max_abs_balanced_face_covector <= tolerance

   capillary_drive_present = not pressure_exact_static
   ```

5. Keep nodal Young--Laplace residuals as solve diagnostics:

   ```text
   young_laplace_normal_residual_linf <= tolerance
   ```

   This is a prerequisite, not the drive definition.

## Pressure Coordinate Design

`pressure_history_mode='pressure_coordinate'` must remain rejected until the
split exposes the scalar pressure coordinate for `L_A(corrected_source)`.

The scalar coordinate is not the component multiplier `mu`; component reaction
has already been removed from `corrected_source`.  The admitted pressure
coordinate must reproduce `pressure_range_face_covectors` under the same
`pressure_flux_kwargs`, gauge, and projection face metric.

Required checks:

```text
pressure_fluxes(pressure_coordinate) == pressure_range_face_covectors
D_f pressure_range == D_f corrected_source
balanced_face == corrected_source - pressure_range
```

## Implementation Sequence

### Commit 1: CPU split oracle

- Add `geometric_capillary_reaction_split.py`.
- Build raw CPU `r_sigma` from `geometric_capillary_riesz_2d`.
- Transfer it to the projection face space through an explicitly tested bridge.
- Use `capillary_external_component_saddle_projection` for the PPE/component
  split.
- Add unit tests with toy operators for range-only, component-only, and mixed
  saddle cases.

### Commit 2: runtime packet integration without GPU production admission

- Convert `GeometricRuntimeCapillaryState` to consume the split.
- Make application norms use split face weights.
- Keep GPU nonzero-sigma runs fail-closed until the GPU split exists.
- Update the existing fail-close tests to require missing projection split,
  not zero-drive-by-construction.

### Commit 3: algebraic capillary-wave gates

- Update `experiment/ch14/diagnose_ao_algebraic_split.py` so rows report:

  ```text
  raw_source_l2
  corrected_source_l2
  pressure_range_l2
  balanced_l2
  bridge_work_residual_linf
  saddle_constraint_linf
  pressure_adjoint_residual
  ```

- Required qualitative gates:

  ```text
  flat:       balanced_l2 ~= 0
  static:     balanced_l2 ~= 0 after component removal
  wave k=1:   balanced_l2 > 0
  wave k=2:   balanced_l2 > k=1 qualitative level
  wave k=3:   balanced_l2 > k=2 qualitative level
  A sweep:    balanced_l2 grows with amplitude
  y+1e-10:    same class as unshifted
  ```

### Commit 4: GPU AO-Fast active projection

- Implement compact projection-face source construction.
- Implement device-resident `L_A(c)` or fail closed where the active PPE cannot
  expose it.
- Implement device-resident component saddle reductions or fail closed.
- No host scalar sync inside PCG/DC/projection candidate loops.
- No dense full-grid Schur/vector allocation in production runtime.

### Commit 5: pressure-coordinate admission

- Expose scalar pressure coordinate from `L_A(corrected_source)`.
- Verify face reconstruction before allowing `pressure_coordinate`.
- Keep `face_acceleration` as the first admitted non-static mode if scalar
  history is not yet proven.

## Rejected Designs

1. Patch `_classify_capillary_pressure_range` to look at
   `max_abs_residual_face_covector` while keeping the GPU zero residual.

2. Treat `geometric_component_volume_reaction_hodge_2d` as production.  It
   lacks active PPE pressure range projection.

3. Split in geometric AO face space and interpolate the residual afterward.
   This can violate the pressure-adjoint metric.

4. Use `capillary_range_projection: component_hodge_augmented` as a hidden
   fallback for AO-Fast.  It is allowed only when the AO split explicitly proves
   it is the same admitted `R_p(q_T)` complement.

5. Accept GPU by running the CPU split under the hood.  That breaks AO-Fast and
   the no hidden dense/CPU fallback policy.

6. Declare `pressure_coordinate` valid from the old Young--Laplace multiplier.
   The coordinate must come from `L_A(corrected_source)`.

## SOLID / A3 / PR Review

- [SOLID-S] Keep the split service separate from `ns_step_services.py`; the
  latter should remain orchestration, not own saddle algebra.
- [SOLID-D] The split must receive projection operations through `div_op`,
  `ppe_solver`, and explicit kwargs; geometry modules must not import concrete
  simulation/PPE classes.
- [A4/A5] `geometry/` owns SP-AO geometric covectors and active tables;
  `simulation/` owns PPE reaction projection.  Do not cross that boundary.
- [PR-5] Every accepted code path must trace back to
  `eq:capillary_pressure_reaction_projection`,
  `eq:capillary_component_saddle`, and
  `eq:capillary_corrected_cochain_and_drive`.
- [PR-1] Do not introduce FD/WENO capillary fixes.  The active PPE/projection
  contract may reuse existing project-approved projection operators only.

## Decision

The strict implementation target is a new simulation-layer split service whose
output makes the existing AO predictor/PPE/corrector skeleton mathematically
honest:

```text
predictor source = corrected_source = r_sigma - B mu
pressure reaction = L_A(corrected_source)
physical drive = corrected_source - L_A(corrected_source)
```

The first code change should be a CPU oracle plus bridge/saddle tests.  GPU
AO-Fast remains fail-closed until the same projection split exists on compact
device-resident active streams.
