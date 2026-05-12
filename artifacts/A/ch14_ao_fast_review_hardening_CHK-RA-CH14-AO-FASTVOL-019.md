# CHK-RA-CH14-AO-FASTVOL-019 — AO-Fast Review Hardening

Date: 2026-05-12

## Purpose

Fix the actionable review findings from the AO-Fast C9 implementation pass
without activating chapter-14 runtime execution.

## Fixes

- Split checkpoint continuation shapes into cell cochains and P1 nodes:
  `state/q`, `state/theta`, and `state/stratum/case_code` are cell-shaped;
  `state/phi` is node-shaped; face histories are validated as 2D staggered
  components `(nx, ny+1)` and `(nx+1, ny)`.
- Closed the mixed-state YAML leak: legacy/default `diffuse_cls` configs now
  reject `bundle_virtual_work`, `closed_interface.endpoint:
  geometric_cell_fraction`, or `constraints: [cell_volume]` unless
  `interface.state_space.kind: geometric_cell_fraction` is explicit.  The
  scan covers both the structured `terms.surface_tension` section and legacy
  `capillary_force` sections so one spelling cannot hide behind the other.
- Made `max_support_stream_ratio` operational in compact support construction
  before halo expansion, kept final active support capacity fail-closed, and
  rejected CUDA/device streams in the temporary host compactor so hidden D2H
  transfer cannot masquerade as GPU-compliant production support compaction.
- Added an explicit no-op ledger for empty active support, avoiding empty
  residual reductions and recording `stop_reason=empty_active_support`.

## Validation

- Local py_compile: PASS for the modified runtime contract, parser, active
  table/projection, and tests.
- Local targeted pytest:
  `pytest -q src/twophase/tests/test_config_state_space.py src/twophase/tests/test_geometry_active_table.py`
  PASS: `29 passed, 1 skipped`.
- Remote-first full suite through `make test` PASS:
  `907 passed, 3 skipped`.
- Earlier remote targeted attempts were rerun after shell quoting/path handling
  caused pytest argument parsing errors; the successful full-suite run is the
  acceptance result.

## SOLID / Negative Knowledge

- [SOLID-S] Checkpoint shape validation, parser front-door rejection, support
  compaction gates, and projection no-op behavior remain separate modules.
- [SOLID-D] The disabled runtime adapter and geometry core depend only on
  narrow contracts, not on chapter-14 experiment wiring.
- [SOLID-X] No chapter-14 runtime activation, experiment result, branch
  deletion, main merge, FD/WENO/PPE fallback, smoothing, clipping, global
  correction, implicit dense fallback, implicit PCG fallback, CPU-first AO
  runtime path, hidden D2H GPU control, or hidden DCCD/UCCD damper was
  introduced.
