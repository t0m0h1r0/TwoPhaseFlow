---
ref_id: WIKI-T-172
title: "AO-Fast Moving-Grid Face-Cochain and Pressure-History Contract"
domain: theory
status: ACTIVE
tags: [ao_fast, geometric_cell_fraction, hfe, pressure_history, face_hodge, grid_rebuild, nonuniform_grid, defect_correction]
sources:
  - path: docs/wiki/cross-domain/WIKI-X-052.md
    description: "Capillary AO-Fast falsification ledger and root cause"
  - commit: 9ddafa77
    description: "Projected face cochain transport across grid rebuild"
  - path: src/twophase/simulation/ns_step_services.py
    description: "Pressure-history coordinate storage and face-law decode"
  - path: src/twophase/simulation/ns_grid_rebuild.py
    description: "Projected face component remap during grid rebuild"
  - path: src/twophase/simulation/velocity_reprojector_basic.py
    description: "FaceHodgeReprojector"
depends_on:
  - "[[WIKI-T-018]]"
  - "[[WIKI-T-034]]"
  - "[[WIKI-T-135]]"
  - "[[WIKI-T-171]]"
  - "[[WIKI-X-050]]"
  - "[[WIKI-X-052]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-14
---

# AO-Fast Moving-Grid Face-Cochain and Pressure-History Contract

## Knowledge Card

AO-Fast on an interface-following nonuniform grid is a discrete differential
complex problem, not just a nodal field update.  The implementation must keep
cell-volume constraints, face Hodge projection, pressure history, and grid
metric epoch consistent.  A capillary run that survives by changing physical
parameters, disabling rebuilds, or adding hidden fallbacks is not a valid AO
solution.

## Theorems

### 1. Smooth-Pressure-History Theorem

The pressure time history used by extrapolation must store a smooth reduced
coordinate.  If the physical pressure contains an interface jump, the jump is
decoded only at the face law where the current geometry and phase traces are
known.  Storing physical jump pressure directly in BDF2 history mixes old
interface geometry with the new metric epoch.

### 2. AO Reaction Locality Theorem

The AO geometric capillary pressure reaction is a current-step constraint
reaction.  It is not a smooth hydrodynamic pressure history variable.  It may
enter the current face law and Schur/Hodge relation, but it must not be carried
forward as if it were the next step's smooth pressure coordinate.

### 3. Face-Cochain Transport Theorem

Let `F^n` be the projected face cochain after the Hodge projection on grid
epoch `G^n`.  After a rebuild to `G^{n+1}`, a nodal interpolation

```text
u^n_nodes -> u^{n+1}_nodes -> face_flux(u^{n+1})
```

does not preserve the face cochain because interpolation, metric Hodge maps,
and discrete divergence do not commute on nonuniform moving grids.

The valid moving-grid transfer is:

```text
F^n on old faces
  -> remap face components on face coordinates
  -> reproject through the new face Hodge metric
  -> F^{n+1} on new faces.
```

If this transfer cannot be proven for a route, the route must fail-close or
discard the projected state through a theory-approved reinitialization.  It may
not silently rebuild fluxes from nodal velocity interpolation.

### 4. Metric-Epoch Theorem

After a grid rebuild, all metric-dependent objects belong to the accepted
epoch: coordinates, widths, face measures, cell volumes, active supports,
pressure-history decoding context, PPE/DC operators, prepared sparse solve
plans, and diagnostic face states.  A mixed-epoch solve is an invalid algebraic
problem even if every array has the right shape.

### 5. Defect-Correction Convergence Theorem

`max_iterations` in defect correction is a cap, not a physical or mathematical
stopping rule.  DC is acceptable only when the residual/compatibility criterion
declares convergence.  HFE was introduced so that the correction is applied to
the right smooth coordinate; it does not justify a fixed-count low-order solve.

## Implementation Contract

- Store pressure history in the smooth reduced coordinate; decode physical jump
  pressure only for the current face law.
- Exclude the AO reaction coordinate from stored smooth pressure history.
- On every accepted grid rebuild, transport `state.projected_face_components`
  as a face cochain and call the new-epoch face Hodge reprojector.
- Rebuild or explicitly invalidate PPE/DC operators, sparse plans, active
  geometry support, and metric caches at the same epoch.
- Keep nonuniform grid metrics and interface-tracking rebuilds enabled in
  production validation.
- Use fail-close solver route selection.  A hidden fallback can mask a violated
  Hodge or convergence contract.

## Code Anchors

- `src/twophase/simulation/ns_grid_rebuild.py`: returns and propagates
  `projected_face_components` through rebuild.
- `src/twophase/simulation/velocity_reprojector_basic.py`:
  `FaceHodgeReprojector.reproject_faces` maps the transported face cochain to
  the new metric.
- `src/twophase/simulation/ns_pipeline.py`: wires projected faces through regular and
  pre-timestep geometric rebuild flows.
- `src/twophase/simulation/ns_step_services.py`: owns pressure-coordinate history and
  current face-law pressure reconstruction.

## Acceptance Evidence

The projected-face rebuild repair converted the capillary 60-step moving-grid
run from explosive to finite:

| Diagnostic | Before | After |
|---|---:|---:|
| `v_abs_max` at step 60 | `5.8e3` | `2.39e-3` |
| `face_hodge_pre` at step 60 | `4.6e7` | `1.17e-3` |
| `ppe_rhs` at step 60 | `2.66e17` | `88.7` |
| `compat` at step 60 | failed route | `4.78e-13` |

Targeted regression coverage includes:

- `test_geometric_grid_rebuild_remaps_projected_face_cochains`;
- `test_face_hodge_reprojector_uses_projection_native_complex`;
- `test_nonstatic_ao_pressure_history_excludes_constraint_reaction_coordinate`;
- `test_affine_pressure_history_coordinate_strips_jump_offset`;
- `test_face_native_predictor_rebuilds_pressure_coordinate_history_faces`;
- `test_ao_pressure_coordinate_history_suppresses_legacy_jump_sigma`.

## Negative Knowledge

The following are theory violations, not tunable implementation details:

- carrying physical jump pressure in smooth BDF2 pressure history;
- storing current AO reaction pressure as future hydrodynamic history;
- rebuilding projected flow by nodal interpolation alone;
- reusing PPE/DC/sparse operators after a metric or coefficient epoch change;
- treating DC iteration count as convergence;
- disabling interface-following rebuilds or nonuniform grids to pass a run.
