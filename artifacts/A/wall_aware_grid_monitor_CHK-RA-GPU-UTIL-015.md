# CHK-RA-GPU-UTIL-015 — Wall-Aware Non-Uniform Grid Monitor

## Scope

User memo "SP-AC - Wall-Aware Non-Uniform Grid Monitor" was checked against
the paper-level grid theory and implemented for the existing non-uniform grid
path only.

## Theory decision

The memo is physically and mathematically admissible.  In wall-bounded
two-phase flow, interface curvature/material jumps and non-slip wall rows
generate independent short length scales.  The grid density must therefore be
an equidistributed composite monitor,

```text
M_a(s) = 1 + A_Gamma,a I_Gamma,a(s) + A_W,a I_W,a(s).
```

The wall term is valid only on non-periodic physical wall sides.  Periodic
boundaries are topological identifications, not walls, so wall refinement is
excluded there to preserve translational symmetry.

The wall term is also not a hidden stabilizer for uniform grids.  YAML parsing
enables it only when the user selected the non-uniform/interface-fitted grid
path globally or for that axis.  Programmatic `GridConfig.wall_refinement_axes`
is treated as an explicit non-uniform-grid request.

## Implementation

- `src/twophase/simulation/config_sections.py` parses `grid.distribution.wall`
  and axis-local wall overrides.
- `src/twophase/config.py` carries normalized wall monitor axes, density
  ratios, widths, and wall sides into the geometry layer.
- `src/twophase/core/grid.py` adds the wall-distance indicator to the existing
  equidistribution monitor and keeps the existing coordinate/metric path.
- Wall-only rebuilds skip unnecessary `psi -> phi` inversion, avoiding extra
  GPU work when no interface monitor is active.
- No operator special-cases the wall-refined grid; all consumers still use
  `coords -> compute_metrics() -> CCD/FCCD/FVM`.

## Verification

- Periodic auto exclusion: `test_wall_refinement_periodic_auto_excluded`.
- Uniform grid exclusion: `test_wall_refinement_requires_nonuniform_grid_selection`.
- Axis-local uniform exclusion: `test_wall_refinement_axis_uniform_excluded`.
- Wall-only symmetry: `test_wall_refinement_wall_only_symmetric`.
- Legacy reduction: `test_wall_refinement_alpha_one_regresses_to_interface_only`.
- Overlap admissibility: `test_wall_interface_overlap_keeps_positive_monotone_cells`.
- Wall shear convergence: `test_wall_refined_grid_wall_shear_derivative_converges`.

## SOLID audit

[SOLID-X] Configuration parsing, geometry generation, and operator evaluation
remain separated.  Legacy interface-only and uniform-grid behavior is retained
through exact reductions (`wall.enabled=false`, `alpha_W=1`, periodic boundary,
or uniform grid selection).  No tested production path was deleted.
