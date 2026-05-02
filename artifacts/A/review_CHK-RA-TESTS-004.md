# CHK-RA-TESTS-004 — Checked-In YAML Reference Cleanup

Date: 2026-05-03
Branch: `ra-tests-cleanup-20260503`
Verdict: PASS

## Scope

- Test files: `src/twophase/tests/test_config_io_fccd.py`, `src/twophase/tests/test_ns_pipeline_fccd.py`.
- Focus: stale checked-in YAML references to removed ch13/static-periodic config files.

## Findings

- Obsolete: several tests still loaded `experiment/ch13/config/*.yaml`, but the active tree no longer has `experiment/ch13/config`.
- Obsolete: `test_ch14_static_droplet_yaml_uses_gpu_static_route` still referenced `ch14_static_droplet_periodic.yaml`; the checked-in route is now `ch14_static_droplet.yaml`.
- Current configs use `affine_jump` interface coupling and FD direct low-order defect base, so old expectations from the ch13 FCCD matrix-free base path were stale.

## Changes

- Repointed capillary and rising-bubble YAML tests to `experiment/ch14/config/ch14_capillary.yaml` and `experiment/ch14/config/ch14_rising_bubble.yaml`.
- Repointed the static-droplet route test to `experiment/ch14/config/ch14_static_droplet.yaml`.
- Updated test names and expectations for current `grid_rebuild_freq`, `affine_jump`, and FD direct defect-correction base behavior.

## Validation

- `git diff --check` PASS.
- Remote targeted pytest PASS for the 7 updated config/solver YAML tests (`7 passed in 0.58s`).

## SOLID-X

- [SOLID-X] No production code changed. Deleted no live implementation coverage; stale file paths and expectations were aligned with checked-in configs.
