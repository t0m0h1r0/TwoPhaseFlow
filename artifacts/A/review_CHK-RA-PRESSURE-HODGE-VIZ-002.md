# CHK-RA-PRESSURE-HODGE-VIZ-002

## Trigger

User correction: masking pressure in a fitted interface band as "undefined" is
itself wrong.  The previous `pressure_bulk` plot hid `0.05 < psi < 0.95` by
writing `NaN`, which made the pressure representative disappear near the
interface instead of testing the affine pressure-work contract.

## Finding

The stored scalar pressure is a representative of an affine pressure-jump
projection, while the physical pressure work is carried by the face cochain.
For visualization, the correct production route is therefore not to hide a
wide fitted-grid band, but to reconstruct a phase-wise Hodge pressure
representative from the saved face cochain:

```
a_f = A_f (G_f p - B_f(j))
```

The runner already stores `pressure_accel_faces` in `data.npz`, so the missing
piece was enforcing that this cochain is mandatory for Hodge pressure plots and
removing the masked fallback from normal figure selection.

## Changes

- Retired `pressure_bulk` from `snapshot_series` registry.
- Kept `masked_bulk_pressure` and `pressure_bulk_snapshot` only as C2
  fail-closed compatibility hooks; both now raise explicit `ValueError`.
- Made `pressure_hodge_snapshot` require `pressure_accel_faces`; it no longer
  falls back to a masked pressure image when the cochain is absent.
- Made `generate_figures` fail closed on figure errors instead of warning and
  silently continuing.
- Promoted `pressure_accel_faces` to checkpoint snapshot persistence, matching
  existing `data.npz` persistence.
- Hardened `_advance_interface_stage` for direct-construction unit tests where
  `_step_diag` is absent; the production Builder still supplies the normal
  diagnostics object.
- Switched all five ch14 production YAML pressure figures to
  `field: pressure_hodge` with `file_prefix: pressure_t`.
- Updated `experiment/ch14/config/README.md` to forbid interface-band masking
  and require data regeneration if the face cochain is absent.

## Image Regeneration

Plot-only regeneration from existing cached `data.npz`:

- `experiment/ch14/results/_tmp_ch14_static_droplet_n64_t1_viz0p2`
  - `pressure_t*.pdf`: 6 Hodge pressure images, regenerated 2026-05-06 13:29.
  - obsolete `pressure_bulk_t*.pdf`: removed.
- `experiment/ch14/results/_tmp_ch14_static_droplet_n32_t4_viz0p2`
  - `pressure_t*.pdf`: 21 Hodge pressure images, regenerated 2026-05-06 13:29.
  - obsolete `pressure_bulk_t*.pdf`: removed.

Both plot-only runs used temporary YAMLs derived from `ch14_static_droplet.yaml`
with only resolution/final time/output/snapshot cadence changed; the temporary
YAMLs were removed afterward to preserve the one-YAML-per-experiment contract.

## Validation

- `pytest src/twophase/tests/test_plot_snapshot_figures.py src/twophase/tests/test_ns_simulation_runner_outputs.py src/twophase/tests/test_simulation_checkpoint.py -q`
  - PASS: `16 passed in 15.21s`
- `pytest src/twophase/tests/test_ns_pipeline_fccd.py::test_ns_pipeline_advances_interface_with_projected_face_velocity src/twophase/tests/test_ns_pipeline_fccd.py::test_ale_discrete_gradient_previous_surface_energy_is_step_local src/twophase/tests/test_plot_snapshot_figures.py src/twophase/tests/test_ns_simulation_runner_outputs.py src/twophase/tests/test_simulation_checkpoint.py -q`
  - PASS: `18 passed in 15.55s`
- `SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test PYTEST_ARGS="twophase/tests/test_plot_snapshot_figures.py twophase/tests/test_ns_simulation_runner_outputs.py twophase/tests/test_simulation_checkpoint.py -q"`
  - Remote wrapper expanded to the full suite.
  - PASS: `587 passed, 32 skipped in 42.35s`
- `make plot EXP=experiment/run.py ARGS="--config _tmp_ch14_static_droplet_n64_t1_viz0p2"`
  - PASS; plot-only from cached `data.npz`
- `make plot EXP=experiment/run.py ARGS="--config _tmp_ch14_static_droplet_n32_t4_viz0p2"`
  - PASS; plot-only from cached `data.npz`

## SOLID-X

No new SOLID violation.  The change is isolated to output contracts, plotting,
snapshot persistence, YAML figure selection, and a diagnostics-availability
guard for direct-construction tests.  It does not alter the projection
equation, pressure-jump assembly, capillary range projection, time-step
selection, or any computational fallback scheme.
