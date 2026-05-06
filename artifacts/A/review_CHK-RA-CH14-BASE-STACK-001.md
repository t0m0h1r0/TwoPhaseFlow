# CHK-RA-CH14-BASE-STACK-001

## User Contract

The canonical ch14 YAML base stack is:

- `128x128` fitted nonuniform interface grid where applicable.
- `transport_variational_p2_ale_discrete_gradient` curvature.
- Ridge--Eikonal reinitialization every step.
- Theory CFL multiplier `cfl: 1.0`.
- FCCD CLS transport + TVD-RK3.
- UCCD6 momentum convection + IMEX-BDF2.
- CCD viscosity + implicit-BDF2 + defect correction with 12 corrections.
- Pressure-jump surface tension.
- FCCD phase-separated affine-jump PPE + defect correction with 12 corrections
  and FD direct low-order base solve.

## Fix

- Replaced the remaining `psi_direct_filtered` ch14 canonical curvature routes
  with `transport_variational_p2_ale_discrete_gradient`.
- Set canonical ch14 Ridge--Eikonal reinitialization cadence to
  `every_steps: 1`.
- Removed the static-droplet frozen-interface/AB2/forward-Euler special route
  and made it use the same dynamic base stack.
- Updated viscosity and PPE defect-correction counts from 3 to 12.
- Updated the oscillating-droplet canonical YAML to the water-air alpha-2
  long-run geometry (`semi_axes: [0.275, 0.225]`, `sigma=0.072`,
  `T_final=40`, `omega0=0.167435`).
- Updated the ch14 config README and in-memory diagnostic variant helper to
  match the canonical base stack.
- Added a regression test that all checked-in ch14 YAMLs share the base
  numerical stack.

Experiment-specific geometry, wall boundary conditions, gravity, output names,
and benchmark final times remain local to each named experiment unless they
were part of the provided droplet base.

## Validation

- `pytest src/twophase/tests/test_config_io_fccd.py -q` PASS (`68 passed`).
- `pytest src/twophase/tests/test_initial_conditions.py::test_ch14_yaml_initial_conditions_use_object_specs -q` PASS.
- Canonical YAML load check PASS: all five use
  `transport_variational_p2_ale_discrete_gradient`, `reinit_every=1`,
  `viscous_dc_max_iterations=12`, and `ppe_dc_max_iterations=12`.
- In-memory diagnostic variants load check PASS.
- Targeted stale signature scan found no remaining ch14 config hits for
  `psi_direct_filtered`, fixed `dt`, frozen static tracking, AB2 static
  convection, forward-Euler static viscosity, `cfl: 0.2`, alpha-4 droplet, or
  DC3.
- `git diff --check` PASS.

## SOLID-X

Config/test/docs alignment only. No production numerical implementation was
deleted or replaced, and no alternate calculation fallback was introduced. Main
merge was not performed.
