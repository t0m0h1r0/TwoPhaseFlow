# CHK-RA-CH14-CFL-POLICY-001

## User Question

`cfl` ではなく `dt` を設定しているのはおかしくないか？

## Finding

Yes. `ch14_static_droplet.yaml` still carried a fixed `run.time.dt`
introduced for a GPU profiling route. That fixed step was an implementation
convenience, not the chapter 7 time-step policy. The canonical ch14 YAML
surface should express the theory CFL multiplier, as the other four production
YAMLs already do.

## Fix

- Replaced `run.time.dt: 0.001235` in `ch14_static_droplet.yaml` with
  `run.time.cfl: 1.0`.
- Updated the static-droplet route test to expect no fixed dt and the standard
  theory CFL policy.
- Added a regression test covering all checked-in ch14 YAMLs so future
  canonical configs reject fixed `dt` and require positive theory-CFL policy.

## Validation

- `pytest src/twophase/tests/test_config_io_fccd.py::test_ch14_static_droplet_yaml_uses_gpu_static_route src/twophase/tests/test_config_io_fccd.py::test_ch14_canonical_yamls_use_theory_cfl_not_fixed_dt -q` PASS.
- `rg -n "\bdt:" experiment/ch14/config/*.yaml` found no checked-in ch14 YAML fixed-dt entries.
- Canonical YAML load check PASS: all five report `dt_fixed=None` and
  `cfl_policy=theory_multiplier`.
- `git diff --check` PASS.

## SOLID-X

Config policy cleanup only. No production numerical implementation changed, no
alternate calculation fallback introduced, and no main merge performed.
