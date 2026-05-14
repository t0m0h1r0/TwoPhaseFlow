# CHK-RA-CH14-AO-FASTVOL-064 - Ch14 capillary visual breakage RCA

## Question

The one-cycle Chapter 14 capillary-wave run produced intermediate plots that
were visibly broken.  The user asked to stop treating the experiment as a blind
run and to identify the cause from physical and mathematical contracts.

## Hypotheses

1. **Young--Laplace sign error.** Rejected.  Earlier artifacts already fixed
   the gross Young--Laplace sign, and flipping the sign contradicts the current
   pressure-reaction split.
2. **DC iteration cap.** Rejected as a root cause.  Increasing the PPE/DC cap
   only masks non-convergence and does not explain an O(1/h) visual blow-up.
   The capillary YAML remains at `max_iterations: 64`.
3. **q/phi gauge ordering for column-height graph tracking.** Confirmed as a
   compatibility bug.  q-primary graph tracking must transport physical cell
   volume first, reconstruct the graph gauge from q, and only then close the
   q/phi compatibility.  Projecting q into the stale old-phi stratum violates
   the gauge owner.
4. **AO face bridge unit error.** Confirmed as the proximate visual-breakage
   cause.  `GeometricRuntimeCapillaryApplicationState` stores
   `predictor_face_acceleration` and `predictor_face_increment` after applying
   the geometric face Hodge inverse.  The NS bridge therefore receives point
   acceleration/increment samples, not integrated face-volume cochains.  Dividing
   them again by `dx` or `dy` multiplies the capillary predictor by O(1/h),
   which is O(10^3) on the nonuniform N32 fitted grid.

## Fix

- `src/twophase/simulation/ns_step_services.py`
  - Updated `_geometric_to_projection_face_pair_2d` to interpolate the
    already-Hodge-divided face field only.  The bridge still uses nonuniform
    metric weights for tensor P1 interpolation and periodic seams, but it no
    longer divides by physical face length.
- `src/twophase/simulation/ns_pipeline.py`
  - Added a q-owned graph-gauge build path after grid rebuild.
  - Deferred in-transport compatibility projection for `column_height_graph`
    until q has been converted back to the configured graph gauge.
- `experiment/ch14/diagnose_ao_stage_chain.py`
  - Added `--prepare-grid-each-step` so the diagnostic can mirror the production
    runner's pre-step grid rebuild path.

## Validation

Remote diagnostic:

```text
make run EXP=experiment/ch14/diagnose_ao_stage_chain.py ARGS="--config experiment/ch14/config/ch14_capillary.yaml --steps 30 --runner-initial-grid-rebuild --prepare-grid-each-step --backend gpu"
```

Result:

- completed in `real 1m22.364s`;
- `ao_compat` stayed about `6e-14`;
- `div_u` stayed at roundoff;
- `predictor_face` grew only from about `3.3e-7` to `1.4e-6`;
- `pressure_face` stayed about `6e-3`;
- PPE/DC converged with the original YAML cap of `64`.

Targeted tests:

```text
make test PYTEST_ARGS="-k ao_face_bridge -q"
make test PYTEST_ARGS="-k column_height_graph_projection_is_deferred_until_q_owned_gauge -q"
make test PYTEST_ARGS="-k ch14_capillary_rebuild_refreshes_ao_state_metric_owner -q"
make test PYTEST_ARGS="-k geometric_grid_rebuild_remaps_projected_face_cochains -q"
git diff --check
```

All passed.

## Remaining Work

The attempted quarter-period production run with `--final-time 0.008899695230`
ran longer than expected and was intentionally stopped rather than treated as
evidence.  The remote orphan process was killed.  Before claiming the one-cycle
visualization is repaired, rerun a bounded production visualization gate after
adding or using an explicit step/final-time gate that returns promptly and
reports GPU/CPU progress.

## SOLID/A3

- [SOLID-S] The bridge fix is local to the face-lattice map; it does not change
  capillary physics, pressure solve policy, CFL, damping, smoothing, or solver
  fallback.
- [SOLID-D] The q-owned graph-gauge build path is selected by the configured
  interface gauge, not by experiment name.
- [SOLID-X] No FD/WENO/PPE fallback, uniform-grid shortcut, interface-tracking
  grid-rebuild removal, tolerance relaxation, hidden fallback, main merge, or
  branch deletion was introduced.
