# CHK-RA-REINIT-TRANSPORT-DIAG-001

Date: 2026-05-06

## Scope

Implement the first concrete SP-AD step: diagnostics that expose whether
Ridge-Eikonal/interface projection changes interface trace energy independently
of physical transport, and whether capillary face cochains remain face-large
after the pressure solve while being divergence-small.

## Implementation

- Added `src/twophase/simulation/interface_projection_diagnostics.py`.
- `PsiDirectTransport` and `PhiPrimaryTransport` now retain the last
  reinit/projection pair `psi_before -> psi_after` for diagnostics.
- `TwoPhaseNSSolver._advance_interface_stage` records:
  - `reinit_triggered`
  - `reinit_volume_delta`
  - `reinit_surface_energy_delta`
  - `reinit_linf_delta`
  - `reinit_zero_level_displacement`
  - `reinit_zero_crossing_change_count`
- The affine pressure-jump path records:
  - `capillary_face_linf`
  - `capillary_face_divergence_linf`
  - `capillary_hodge_residual`
- Added targeted tests in `test_interface_projection_diagnostics.py`.

No solver fallback, damping, CFL tuning, curvature cap, smoothing, or alternate
calculation scheme was introduced.

## Validation

Local:

- `py_compile` targeted touched files: PASS.
- `pytest src/twophase/tests/test_interface_projection_diagnostics.py -q`:
  4 passed.
- `pytest src/twophase/tests/test_ns_pipeline_fccd.py -k 'adaptive_reinitializes or mass_correction or affine_jump' -q`:
  8 passed, 53 deselected.
- `pytest src/twophase/tests/test_diagnostics.py src/twophase/tests/test_ns_simulation_runner_outputs.py -q`:
  21 passed.
- `pytest src/twophase/tests/test_interface_stress_closure.py -k 'transport_variational_p2_discrete_gradient or transport_variational_p2_ale_discrete_gradient or affine_jump' -q`:
  11 passed, 15 deselected.
- `git diff --check`: PASS.

Remote GPU smoke:

Temporary config `_tmp_spad_projection_diagnostics.yaml` was derived from the
static-droplet route with `N=32`, `T=0.02`, `step_diagnostics=true`, and
`reinit_every=1`; it was removed after the run.

Command:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle \
  EXP=experiment/run.py \
  ARGS="--config _tmp_spad_projection_diagnostics --no-checkpoint-final"
```

Result: PASS, pulled `experiment/ch14/results/_tmp_spad_projection_diagnostics/data.npz`.

Selected debug arrays:

```text
reinit_triggered                  [0, 1, 1]
reinit_volume_delta               [0, -2.62e-13, -4.75e-13]
reinit_surface_energy_delta       [0, -1.280e-02, 1.681e-03]
reinit_zero_crossing_change_count [0, 144, 32]
reinit_zero_level_displacement    [0, 0, 7.495e-03]
capillary_face_linf               [1.137e-03, 7.762e-03, 9.642e-03]
capillary_face_divergence_linf    [2.885e-09, 2.153e-03, 4.472e-02]
capillary_hodge_residual          [1.137e-03, 7.762e-03, 9.642e-03]
```

Interpretation: volume correction alone is insufficient as an acceptance
criterion.  The reinitialization/projection can preserve volume to roundoff
while still changing trace energy and zero-crossing topology.  The face-cochain
diagnostics also expose the separate face norm and divergence budget needed for
the next range-projection/Hodge gate.

## Next

The next implementation unit should promote the current
`capillary_hodge_residual` proxy into a true `A_f G_f` range projection residual
and add a static-droplet fail-closed gate.
