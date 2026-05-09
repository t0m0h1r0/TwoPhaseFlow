# CHK-RA-CH14-GRAVITY-HODGE-IMPL-001

## Scope

Implemented the variational gravity Hodge route for the rising-bubble stack.
Gravity is now available as a face-native covector constructed from the exact
common-flux mass-transport adjoint, rather than as a nodal residual body-force
split.

## Implemented Contract

- Shared exact FCCD transport adjoint:
  `twophase.core.transport_adjoint.negative_face_divergence_adjoint`.
- Simulation re-export:
  `twophase.simulation.transport_adjoint`.
- Gravity covector:
  `twophase.simulation.gravity_covector.build_variational_gravity_faces`.
- Predictor integration:
  `variational_potential` disables legacy `buoy_v` and adds
  `dt * a_g` directly to `predictor_face_components`, after applying the same
  wall normal/no-slip face constraint as the predictor state.
- Corrector integration:
  gravity is not added to `state.f_y`, so the pressure/capillary corrector
  cannot double-count it.
- YAML UX:
  `numerics.momentum.terms.gravity.formulation: variational_potential`,
  `transport_adjoint: common_flux`, `metric: transported_face_mass`,
  `hodge_gate: fail_close`, `work_gate: diagnostic`.
- Fail-close gates:
  the variational route rejects legacy balanced predictor assembly, missing
  face-native projection state, projection-consistent buoyancy, non-common-flux
  momentum, wrong pressure force contract, wrong scalar operator pairing, and
  periodic gravity axis.

## Theory Checks

The unit test `test_variational_gravity_covector_matches_common_flux_mass_virtual_work`
verifies

```text
<r_g, w_f> + <d Phi_g / dm, -D_f(rho_f w_f)> = 0
```

with the same FCCD `face_divergence` used by the conservative common-flux
transport.  This is the exact discrete virtual-work identity for the
implemented transport map, not a continuum analogy.

The periodic-axis rejection follows from the absence of a single-valued
gravitational potential on a periodic vertical coordinate.

The constrained single-phase test verifies that, after applying the physical
wall-normal velocity constraint, the gravity acceleration has zero horizontal
component, zero wall-normal boundary faces, and interior vertical acceleration
equal to `-g`.

## Validation

- `git diff --check`: PASS.
- Remote pytest wrapper: PASS, `640 passed, 33 skipped in 42.25s`.
- Remote N=32x64 rising-bubble probe, T=0.001, same YAML route:
  - completed `142` steps to `t_final=0.001`;
  - final kinetic energy `1.5235568496891475e-06`;
  - max volume drift `7.492770403123784e-08`;
  - mean rise velocity `5.68451170884911e-05 -> 0.007590405569496238`;
  - generated `psi`, `velocity`, `pressure`, diagnostics PDFs, and restart
    checkpoints under
    `experiment/ch14/results/_tmp_ch14_rising_bubble_variational_gravity_n32_t0001/`.

## Residual Risk

This CHK proves the new force route is algebraically adjoint-compatible and can
run the early rising-bubble window without immediate blow-up.  It does not yet
prove the previous long-time blow-up band is eliminated; that requires a
longer staged run, preferably after adding a cheaper run variant so full
verification does not require editing canonical YAML or running the heavy
128x256 reference configuration.
