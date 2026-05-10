# CHK-RA-CH14-DROPLET-INVARIANT-001

## Question

The oscillating droplet visibly lost liquid volume.  The root question was not
how to tune the run, but which discrete invariant the code was preserving.

For a closed incompressible droplet in a periodic domain, the physical invariant
is the geometric liquid volume

```text
V_Gamma = |Omega_l(Gamma_h)|
```

represented here by the P1 marching-squares area of the closed interface.  The
diffuse CLS integral

```text
M_psi = sum_i psi_i dV_i
```

is a profile coordinate.  It is useful for diffuse advection diagnostics, but it
is not the hard physical volume of a closed sharp interface.

## Hypotheses

| ID | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | The volume loss is true Rayleigh--Lamb physics. | Rejected | Incompressible closed droplet area should not shrink; only shape oscillates. |
| H2 | The snapshot only looks smaller because the plotted diffuse band changes. | Rejected as sole cause | P1 sharp area itself lost O(10%) under `diffuse_mass`. |
| H3 | The dynamic fitted grid changes the physical domain measure. | Supported, secondary | Periodic `cell_volumes()` previously counted image nodes; area sum was above the physical domain. |
| H4 | Reinit preserves the wrong scalar. | Supported, primary | `diffuse_mass` direct reinit lost about 20.9% sharp area; `sharp_phase_volume` direct reinit preserved P1 area to about 1e-6 relative. |
| H5 | `sharp_phase_volume` failed because the shift bracket was too narrow. | Rejected | The fail-close came after the sharp shift, during a second diffuse-mass profile-width constraint. |
| H6 | Sharp volume and diffuse mass can both be hard constraints on a fixed zero set. | Rejected | With fixed zero level, profile-width mass has a bounded image; the old diffuse target can be outside it. |
| H7 | Transport can preserve diffuse `psi` mass while changing sharp area. | Supported | Short-step `diffuse_mass` kept a diffuse integral but lost about 17.0% sharp area by step 20. |
| H8 | Reinit was targeting the post-transport area, not the step-start area. | Supported | Plumbing inspection showed `reinitialize(psi_after_transport)` measured its own target from that input. |
| H9 | Dynamic grid remap was a third projection that restored diffuse mass, not sharp area. | Supported | After fixing transport target, scheduled grid rebuild still moved sharp area until rebuild used the pre-remap sharp target. |
| H10 | A wall half-cell control-volume change can be bundled into this fix. | Rejected for this patch | It perturbs existing phase-separated PPE Hodge/gauge contracts. This patch only quotients periodic image nodes and leaves non-periodic nodal metrics unchanged. |

## Implemented Contract

1. `Grid.cell_volumes()` is now boundary-topology aware.
   Periodic terminal image planes carry zero independent measure and the source
   plane receives the wrapped half-cell contribution.  Non-periodic axes keep
   the existing nodal metric until the pressure/FCCD Hodge contracts are
   updated as a separate theory/implementation unit.

2. `RidgeEikonalReinitializer(sharp_phase_volume)` preserves only
   `V_Gamma`.  It no longer tries to restore diffuse mass by changing the
   sigmoid profile width after the sharp zero-level correction.

3. `PsiDirectTransport` and `PhiPrimaryTransport` pass the pre-transport sharp
   volume target to compatible reinitializers, so reinit restores the step-start
   closed-droplet volume instead of preserving the already-drifted transported
   interface.

4. Dynamic grid rebuild records the pre-remap sharp volume and applies the same
   sharp-volume retraction after remapping onto the new fitted grid.

5. `experiment/ch14/config/ch14_oscillating_droplet.yaml` now uses
   `volume_constraint: sharp_phase_volume`.

## Short Validation

Local 20-step diagnostic:

```text
METRIC_AUDIT grid_dV_sum=4.000000000000e-04
periodic_unique_area=4.000000000000e-04
rel_overcount=+0.000000e+00

DIRECT_REINIT dynamic_diffuse sharp_area_rel=-2.085142e-01
DIRECT_REINIT dynamic_sharp   sharp_area_rel=-1.212671e-06

SHORT_STEP dynamic_diffuse step=20 sharp_area_rel=-1.704779e-01
SHORT_STEP dynamic_sharp   step=20 sharp_area_rel=-1.428814e-03
```

The remaining `1.4e-3` sharp-area drift over 20 local CPU steps is no longer the
old invariant mix-up; it is the residual of using smooth `psi` transport plus
global sharp retraction instead of a true geometric cell-fraction transport
state.  The geometric `q_C=|C|theta_C` route in SP-AO is the fully discrete
theory endpoint.

## Validation Commands

```text
/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python -m pytest \
  src/twophase/tests/test_uniform_alpha1_equivalence.py \
  src/twophase/tests/test_ridge_eikonal.py \
  src/twophase/tests/test_config_io_fccd.py \
  src/twophase/tests/test_fccd_advection_levelset.py::test_sharp_reinit_receives_pre_transport_volume_target \
  src/twophase/tests/test_common_flux_transport.py::test_conservative_grid_rebuild_preserves_phase_and_momentum_integrals \
  src/twophase/tests/test_ns_pipeline.py::test_rebuild_grid_mass_conservation \
  src/twophase/tests/test_ns_pipeline_fccd.py::test_phase_separated_pressure_jump_stack_one_step_no_nan -q
```

Result: `122 passed, 3 skipped`.

```text
/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python \
  experiment/ch14/diagnose_droplet_volume_rca.py --steps 20
```

Result: values shown above.

```text
PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH make test-local
```

Result on this branch: `660 passed, 33 skipped`, with two failing tests that
also fail on current `main`:

- `test_ch14_capillary_wave_yaml_builds_initial_field`
- `test_ch14_capillary_curvature_is_supported_on_interface_band`

`make test` attempted the project default remote-first route, but the wrapper
reported remote unavailable and then local fallback lacked `python` on `PATH`.
