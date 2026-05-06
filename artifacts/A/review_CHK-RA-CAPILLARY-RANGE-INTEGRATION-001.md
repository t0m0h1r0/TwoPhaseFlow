# CHK-RA-CAPILLARY-RANGE-INTEGRATION-001

Date: 2026-05-06

## Scope

Integrate the capillary range-Hodge result into the production pressure-jump
logic and expose the selected closure in canonical YAML.

## Theory

For affine pressure jumps, the face cochain entering momentum is
`a_f = A_f G_f p - c_f`, where `c_f = A_f B_Gamma(j)` is the capillary jump
cochain.  Static Young-Laplace equilibrium requires `a_f = 0` for a circular
droplet.  If `c_f` is not in `range(A_fG_f)`, the PPE can match
`D_f c_f` while leaving a divergence-free Hodge component in `a_f`; that
component is not detected by `D_f a_f` but injects kinetic energy.

The implemented closure replaces `c_f` in the velocity/corrector face work by
`Pi_{range(A_fG_f)} c_f`.  Since the projection preserves `D_f c_f` up to the
PPE residual, the projection constraint is unchanged while the non-range
capillary artifact is excluded from the pressure-jump force.

## Implementation

- Added `numerics.projection.poisson.operator.capillary_range_projection`.
- Supported modes:
  - `none`
  - `range_projected`
- `range_projected` requires `interface_coupling: affine_jump`.
- `FCCDDivergenceOperator.pressure_fluxes()` can now consume a projected
  capillary jump face cochain directly.
- `solve_ns_pressure_stage()` computes the range projection in the main path
  when configured, uses it for `pressure_accel_face_components` and
  `pressure_correction_face_components`, and still records the original
  Hodge residual in debug diagnostics.
- ch14 canonical YAMLs now set
  `capillary_range_projection: range_projected`.

No damping, CFL tuning, curvature cap, smoothing, FD/WENO fallback, or
unlabelled alternate calculation route was introduced.

## Validation

Local:

- Targeted `py_compile`: PASS.
- `pytest src/twophase/tests/test_interface_projection_diagnostics.py src/twophase/tests/test_config_io_fccd.py -q`:
  75 passed.
- `pytest src/twophase/tests/test_ns_pipeline_fccd.py -k 'range_projected_capillary_jump or affine_jump or phase_separated' -q`:
  18 passed, 44 deselected.
- `git diff --check`: PASS.

Remote GPU smoke:

Temporary config `_tmp_range_projected_static_n32_t0p2.yaml` was derived from
the static-droplet route with `N=32`, `T=0.2`, `debug=true`, and
`capillary_range_projection: range_projected`; it was removed after the run.

Command:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle \
  EXP=experiment/run.py \
  ARGS="--config _tmp_range_projected_static_n32_t0p2 --no-checkpoint-final"
```

Result: PASS, pulled
`experiment/ch14/results/_tmp_range_projected_static_n32_t0p2/data.npz`.

Selected final/max values:

```text
t_final                                  0.2
KE_final                                 7.783046e-38
volume_drift_final                       1.776544e-15
deformation_final                        0
capillary_face_linf_max                  3.816392e-17
capillary_face_divergence_linf_max       4.027837e-15
capillary_jump_linf_max                  2.780542e-02
capillary_range_projection_linf_max      2.784585e-02
capillary_hodge_residual_max             1.139486e-03
capillary_hodge_divergence_linf_max      2.885150e-09
div_u_max                                1.282178e-17
ppe_rhs_max                              5.043980e-15
ppe_dc_converged                         1 for every recorded step
```

Interpretation: the raw capillary jump still has the same measurable Hodge
residual, but the face cochain actually used in the velocity correction is
reduced to roundoff.  The static droplet no longer receives the previously
identified non-range capillary acceleration.

## Next

Run longer static-droplet and dynamic ch14 checks after this integration to
quantify long-time equilibrium and dynamic response, then revisit the
P2-ALE pressure-jump route under the now range-projected closure.
