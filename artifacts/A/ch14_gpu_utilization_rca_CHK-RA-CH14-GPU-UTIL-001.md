# CHK-RA-CH14-GPU-UTIL-001 - ch14 oscillating-droplet GPU utilization RCA

Date: 2026-05-08
Branch: `codex/ra-ch14-gpu-util-20260508`
Worktree: `.claude/worktrees/codex-ra-ch14-gpu-util-20260508`
Implementation commit: `766fa7e1`

## Scope

Targeted ResearchArchitect review of the canonical
`ch14_oscillating_droplet` GPU execution path, focusing on periodic drops to
0% GPU utilization without changing the declared ch14 numerical contract.

## Findings

### F1 - sharp volume correction fell back to host geometry

`ch14_oscillating_droplet.yaml` reinitializes every step and uses
`volume_constraint: sharp_phase_volume`.  The ridge-eikonal volume multiplier
therefore calls the sharp P1 volume functional at every reinitialization, and
the bracketing/bisection loop may evaluate it many times.  On GPU,
`liquid_area_2d()` previously copied the whole nodal field to host and walked
cells in Python.  This is the strongest periodic GPU-idle source in the
reviewed path.

Fix: `marching_squares_liquid_area_2d()` now evaluates the same fixed P1
marching-squares area on `backend.xp`.  The ridge-eikonal GPU path also
measures shifted signed-distance volume directly at `phi=0` when no wall
closure/contact pinning is active.  This avoids materializing a trial sigmoid
field for every scalar shift while preserving the sharp CLS equivalence
`psi >= 0.5` iff `phi >= 0`.  CPU and wall-contact paths keep the legacy
materialized-psi route.

### F2 - closed-interface stratum built topology from a full host copy

`closed_interface_riesz_cochain()` uses the fixed-stratum descriptor in the
production pressure-jump path.  The descriptor previously copied the whole
`psi` field to NumPy and computed sign/cut topology in Python.

Fix: cell cases, edge-crossing counts, and threshold-touch counts are now
computed on `backend.xp`; only compact `uint8` topology arrays and one scalar
diagnostic are transferred to host for hashing/metadata.

### F3 - snapshots retained unused reinit intermediate fields

At snapshot cadence, `run_simulation()` forced storage of
`psi_before_transport`, `psi_after_transport_before_reinit`, and
`psi_after_reinit` whenever any snapshot was due.  The canonical ch14 figures
request `psi`, `velocity`, and `pressure_hodge`, so these hidden intermediate
fields caused avoidable device-to-host copies.

Fix: the runner now records projection intermediate fields only when a
configured `snapshot_series` explicitly requests one of those fields.

## Remaining GPU sync points

- Snapshot output still copies configured fields to host; this is an I/O
  boundary and is required for requested figures.
- `DiagnosticCollector` still performs per-step scalar reductions; these are
  batched scalar transfers, not full-field geometry fallbacks.
- `NonUniformFMM._solve_gpu` remains a low-occupancy exact heap kernel with a
  scalar status check.  It was not changed because replacing accepted-set
  ordering would be an algorithmic deviation, not a GPU optimization.

## Validation

- `git diff --check`: PASS.
- Local targeted tests:
  `PYTHONPATH=src /Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 -m pytest src/twophase/tests/test_closed_interface_geometry.py src/twophase/tests/test_ridge_eikonal.py src/twophase/tests/test_ns_simulation_runner_outputs.py -q`
  -> `47 passed, 3 skipped`.
- Remote-first GPU/full-suite validation:
  `SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test PYTEST_ARGS='twophase/tests/test_closed_interface_geometry.py twophase/tests/test_ridge_eikonal.py twophase/tests/test_ns_simulation_runner_outputs.py -q --gpu'`
  -> `839 passed, 3 skipped`.
- Remote ch14 oscillating-droplet smoke:
  `SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS='--config _tmp_ch14_gpu_util_smoke --no-checkpoint-final'`
  -> N=32, 3 steps completed; capillary limiter active; no checkpoint/figure
  output retained.

## SOLID

[SOLID-X] The change keeps the declared sharp P1 geometry and ridge-eikonal
volume constraint, moves GPU hot-path geometry to `backend.xp`, and removes
unrequested snapshot retention.  No tested implementation was deleted, and no
FD/WENO/PPE fallback, damping/CFL workaround, smoothing, curvature cap,
benchmark-name branch, blanket projection, or QP-as-physics path was added.
