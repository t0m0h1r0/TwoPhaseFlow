# CHK-RA-CH14-YAML-CONSOLIDATION-001

## User Request

- Reduce excess YAML files.
- Record correct contents.
- Keep at most one YAML file per experiment type.

## Decision

`experiment/ch14/config` is now constrained to the five production experiment
types:

- `ch14_capillary.yaml`
- `ch14_static_droplet.yaml`
- `ch14_oscillating_droplet.yaml`
- `ch14_rising_bubble.yaml`
- `ch14_rayleigh_taylor.yaml`

The removed N64, one-period, static-grid, and differential-control files were
diagnostic variants, not separate experiment types. They are no longer checked
in as YAML files.

## Fix

- Deleted six redundant checked-in YAML variants under `experiment/ch14/config`.
- Added `experiment/ch14/config_variants.py` so legacy diagnostic scripts can
  derive historical N64 controls from the canonical YAMLs in memory.
- Updated the ch14 config README to state the one-YAML-per-experiment policy.
- Updated the short-paper memo and wiki source path so the N64 one-period run
  is described as an archived result identity derived from the canonical
  oscillating-droplet YAML, not as a checked-in YAML.
- Strengthened `test_ch14_yaml_initial_conditions_use_object_specs` to reject
  any future extra ch14 YAML.

## Validation

- `python -m pytest src/twophase/tests/test_initial_conditions.py::test_ch14_yaml_initial_conditions_use_object_specs -q` PASS.
- `python -m py_compile experiment/ch14/config_variants.py ...` PASS for the
  touched ch14 diagnostic scripts.
- Canonical YAML load check PASS: exactly five YAMLs found and all load through
  `ExperimentConfig.from_yaml`.
- In-memory variant load check PASS for static baseline/static-grid and
  oscillating baseline/one-period controls.
- `git diff --check` PASS.

## SOLID-X

No production numerical scheme was changed, no tested implementation was
deleted, and no main merge was performed. This is a config-surface cleanup:
diagnostic variants remain reproducible as explicit in-memory derivations from
canonical experiment YAMLs.
