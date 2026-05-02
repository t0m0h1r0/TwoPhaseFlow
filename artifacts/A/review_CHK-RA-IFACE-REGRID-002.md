# CHK-RA-IFACE-REGRID-002 — Every-Step Interface-Following Grid Default

Date: 2026-05-03
Branch: `ra-interface-reconstruction-theory-20260503`
Verdict: PASS AFTER CORRECTION

## Correction

- CHK-RA-IFACE-REGRID-001 overcorrected by treating the ALE/GCL/remap theory as a fail-closed blocker.
- The corrected interpretation is constructive: every-step interface-following rebuild is the standard route, and the theory defines the split remap/reprojection closure that makes it admissible.
- Explicit `schedule: static` / `0` remains available only for fixed-grid comparison cases.

## Changes

- Restored ch14 canonical configs to `grid.distribution.schedule: 1`.
- Made interface-fitted configs default to every-step rebuild when `schedule` is omitted.
- Removed the runtime rejection of `grid_rebuild_freq > 0`.
- Documented `rebuild_ns_grid` as the standard split rebuild/remap/reprojection helper.
- Rewrote Chapter 10 and Appendix D wording so Mode 2 is the standard interface-following path, not an unimplemented path.

## A3 Traceability

- Equation: `eq:mesh_velocity_regrid`, `eq:ale_grid_gcl`, `eq:ale_conservative_update`, `eq:regrid_face_geometry`.
- Discretization: physical transport is followed by interface-fitted grid reconstruction, volume-corrected `psi` remap, velocity remap, pressure-cache invalidation, history reset, and velocity reprojection.
- Code: `_parse_grid` defaults fitted-grid schedules to `1`; `TwoPhaseNSSolver` / `SolverInterfaceOptions` default `grid_rebuild_freq=1`; `normalise_ns_interface_runtime` accepts positive rebuild intervals.
- Tests/configs: `test_dynamic_grid_rebuild_schedule_is_default_for_fitted_solver`, `test_gridcfg_interface_fitting_defaults_to_every_step_rebuild`, and ch14 YAML schedule assertions.

## Validation

- `git diff --check` PASS.
- Remote targeted pytest PASS: `dynamic_grid_rebuild_schedule_is_default_for_fitted_solver`.
- Remote targeted pytest PASS: `ch14_capillary_yaml_uses_true_low_order_defect_base`.
- Remote targeted pytest PASS: `gridcfg_parse_alpha_grid`.
- Remote targeted pytest PASS: `gridcfg_interface_fitting_defaults_to_every_step_rebuild`.
- Remote targeted pytest PASS: `axis_local_interface_fitting_parse`.
- Touched-section KL-12 literal-dollar scan PASS.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` PASS, producing `paper/main.pdf` with 242 pages.
- `paper/main.log` undefined/citation/multiply-defined grep clean.

## SOLID-X

- [SOLID-X] No new violation found. Schedule policy remains in config/runtime normalization, rebuild mechanics remain in `ns_grid_rebuild`, and solver/PPE responsibilities remain separated.
- [SOLID-X] No tested implementation was deleted. Static scheduling remains explicit; every-step rebuild is the default interface-fitted route.
