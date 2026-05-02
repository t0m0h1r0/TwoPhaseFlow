# CHK-RA-IFACE-REGRID-001 — Interface-Following Grid Reconstruction Theory

Date: 2026-05-03
Branch: `ra-interface-reconstruction-theory-20260503`
Verdict: SUPERSEDED BY CHK-RA-IFACE-REGRID-002

## Scope

- Theory: interface-following, interface-fitted grid reconstruction as a paper-standard path.
- Paper: Chapter 9 split-PPE guard, Chapter 10 grid/ALE section, Chapter 11 timestep gate, Appendix D ALE note, and Chapter 15 summary.
- Code: dynamic non-uniform grid rebuild scheduling, ch14 canonical configs, and targeted regression tests.

## Finding

- The current paper correctly warned that Mode 2 moving-grid rebuilds require ALE and all-field remapping, but it did not yet state the closed mathematical contract.
- A paper-standard moving fitted grid must satisfy four coupled gates: discrete geometric conservation law, ALE conservative update or equivalent conservative remap, consistent reset/reconstruction of all history quantities, and current-grid reconstruction of jump/HFE face data.
- Superseded correction: this review incorrectly treated missing monolithic ALE as a reason to reject scheduled dynamic rebuilds. CHK-RA-IFACE-REGRID-002 restores every-step interface-following rebuild as the standard split remap/reprojection path.

## Changes

- Added equations for mesh velocity, discrete GCL, ALE conservative update, and current-grid interface face geometry reconstruction.
- Updated pressure-jump and timestep sections so grid rebuild completeness depends on those equations, not on `psi` remapping alone.
- Superseded by CHK-RA-IFACE-REGRID-002: ch14 standard YAMLs use `schedule: 1`, and positive schedules are allowed.
- Kept the tested `_rebuild_grid` helper for initial fitted-grid construction and direct diagnostics; no tested implementation was deleted.

## A3 Traceability

- Equation: `eq:mesh_velocity_regrid`, `eq:ale_grid_gcl`, `eq:ale_conservative_update`, `eq:regrid_face_geometry`.
- Discretization: moving tensor-product grid must preserve cell volumes by GCL and update conserved variables with relative face velocity `u - v_mesh`.
- Code after correction: `normalise_ns_interface_runtime` allows positive `grid_rebuild_freq`; `rebuild_ns_grid` is the split rebuild/remap/reprojection helper.
- Tests/configs after correction: `test_dynamic_grid_rebuild_schedule_is_default_for_fitted_solver`, ch14 canonical YAMLs, and `test_ch14_capillary_yaml_uses_true_low_order_defect_base`.

## Validation

- `git diff --check` PASS.
- Superseded validation item: fail-closed regression was removed in CHK-RA-IFACE-REGRID-002.
- Remote targeted pytest PASS: `ch14_capillary_yaml_uses_true_low_order_defect_base`.
- Touched-section KL-12 scan PASS with literal `$` search.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` PASS, producing `paper/main.pdf` with 242 pages.
- `paper/main.log` undefined/citation/multiply-defined grep is clean except the package-name line for `rerunfilecheck`.

## SOLID-X

- [SOLID-X] No new violation found. Runtime gating stays in interface-runtime normalization, grid remap mechanics remain isolated in `ns_grid_rebuild`, and no solver/PPE responsibilities were mixed.
- [SOLID-X] No tested implementation was deleted. The legacy direct rebuild helper remains available for initial construction and diagnostics, while scheduled dynamic use is rejected until the paper-standard closure exists.
