# CHK-RA-CAPILLARY-RANGE-DIAG-001

Date: 2026-05-06

## Scope

Promote the capillary face diagnostic from a post-PPE face-norm proxy to the
actual discrete range residual
`c_f - Pi_{range(A_f G_f)} c_f`, using the same affine cut-face coefficient
as the PPE/corrector path.

## Implementation

- `capillary_jump_range_projection()` now extracts the pressure-jump cochain
  `c_f` by evaluating the affine pressure flux at zero pressure.
- It solves `D_f A_f G_f q = D_f c_f` with the same jump-aware cut-face
  density coefficient but with the jump value set to zero.
- It records:
  - `capillary_jump_linf`
  - `capillary_range_projection_linf`
  - `capillary_hodge_residual`
  - `capillary_hodge_divergence_linf`
  - `capillary_range_projection_solved`
- The diagnostic solve snapshots and restores the PPE solver graph, so the
  production PPE diagnostics/history from the real step are not overwritten.
- The existing velocity correction and pressure-jump scheme are not altered.

No damping, CFL tuning, smoothing, curvature cap, FD/WENO fallback, or
unlabelled alternate calculation scheme was introduced.

## Validation

Local:

- Targeted `py_compile`: PASS.
- `pytest src/twophase/tests/test_interface_projection_diagnostics.py -q`:
  5 passed.
- `pytest src/twophase/tests/test_ns_pipeline_fccd.py -k 'affine_jump_pressure_stack_one_step_no_nan or affine_jump_pressure_stage_stores_history_faces or affine_jump_pressure_history_faces_store_full_cochain' -q`:
  3 passed, 58 deselected.
- `pytest src/twophase/tests/test_diagnostics.py src/twophase/tests/test_ns_simulation_runner_outputs.py -q`:
  21 passed.
- `git diff --check`: PASS.

Remote GPU smoke:

Temporary config `_tmp_spad_range_projection_n32_t0p2.yaml` was derived from
the static-droplet route with `N=32`, `T=0.2`, `step_diagnostics=true`, and
`reinit_every=0`; it was removed after the run.

Command:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle \
  EXP=experiment/run.py \
  ARGS="--config _tmp_spad_range_projection_n32_t0p2 --no-checkpoint-final"
```

Result: PASS, pulled
`experiment/ch14/results/_tmp_spad_range_projection_n32_t0p2/data.npz`.

Selected final/max values:

```text
t_final                                  0.2
KE_final                                 2.235190e-07
volume_drift_final                       5.075840e-16
deformation_final                        0
capillary_jump_linf_max                  2.780308e-02
capillary_range_projection_linf_max      2.784466e-02
capillary_hodge_residual_max             1.152882e-03
capillary_hodge_divergence_linf_max      2.885150e-09
capillary_range_projection_solved        1 for every recorded step
ppe_dc_converged                         1 for every recorded step
ppe_dc_final_relative_l2_max             2.278601e-09
```

Interpretation: the static droplet still leaves an essentially
divergence-free Hodge component of about `1.15e-3` in the capillary face
cochain.  This is the discrete residual that the previous proxy was pointing
at: it is not a PPE convergence failure, and it is not visible from
`D_f a_f` alone.  The next correction must change the capillary jump cochain
itself so that the circular Young-Laplace state is in `range(A_fG_f)` to the
static-droplet tolerance.

## Next

Add a fail-closed static-droplet Hodge gate and then derive a corrected
face-cochain construction for the circular Young-Laplace identity.  Do not
remove the Hodge component generically: away from static equilibrium it is the
solenoidal capillary force that can drive physical motion.
