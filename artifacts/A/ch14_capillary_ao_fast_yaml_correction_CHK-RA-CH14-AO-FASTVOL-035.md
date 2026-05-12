# CHK-RA-CH14-AO-FASTVOL-035 — Ch14 Capillary AO-Fast YAML Correction

## Trigger

User review identified that the capillary-wave YAML was still configured as
the standard diffuse-CLS route even though the intended recent experiment was
the AO-Fast capillary-wave route.

## Correction

- Updated `experiment/ch14/config/ch14_capillary.yaml` to declare
  `interface.state_space.kind: geometric_cell_fraction`.
- Restored the full AO-Fast front-door contract:
  `q` carrier, `theta` normalized view, P1 `phi` gauge, active-cached
  hard-cell-volume compatibility, required GPU storage, forbidden inner
  host transfers, forbidden dense runtime fallback, and `fallback.policy: none`.
- Switched interface transport from diffuse `psi`/FCCD to
  `q`/`geometric_swept_volume` with certified boundedness and fail-close.
- Disabled Ridge--Eikonal reinitialization for the capillary-wave YAML
  (`algorithm: none`, `every_steps: 0`) because AO compatibility projection is
  not a diffuse redistance step.
- Switched capillary source from `curvature_jump` to `bundle_virtual_work` and
  routed the PPE capillary contract through
  `capillary_reaction_projection: pressure_component_hodge`.
- Updated parser/solver tests and Chapter 14 config documentation so future
  checks distinguish the AO-Fast capillary YAML from the remaining diffuse-CLS
  Chapter 14 YAMLs.
- Updated wiki cards `WIKI-T-169` and `WIKI-X-049` to remove the stale claim
  that the checked-in capillary-wave YAML is diffuse-CLS.

## Validation

- Remote-first `make test PYTEST_ARGS='twophase/tests/test_config_io_fccd.py::test_ch14_capillary_yaml_loads_execution_stack twophase/tests/test_config_io_fccd.py::test_ch14_canonical_yamls_share_base_numerical_stack twophase/tests/test_ns_pipeline_fccd.py::test_ch14_capillary_yaml_builds_solver twophase/tests/test_ns_pipeline_fccd.py::test_ch14_capillary_wave_yaml_builds_initial_field twophase/tests/test_ns_pipeline_fccd.py::test_ch14_rayleigh_taylor_curvature_is_supported_on_interface_band twophase/tests/test_ns_pipeline_fccd.py::test_ch14_capillary_yaml_uses_true_low_order_defect_base -q'`
  executed on the remote pytest target.  The make target expanded to the full
  suite and passed: `710 passed, 33 skipped`.
- `git diff --check` passed.

## Non-Changes

- No CFL reduction, damping, smoothing, curvature cap, clipping repair, hidden
  PCG/DC fallback, dense-AO runtime fallback, or main merge was introduced.
