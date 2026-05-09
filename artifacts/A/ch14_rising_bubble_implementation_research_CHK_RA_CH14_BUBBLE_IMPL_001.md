# CHK-RA-CH14-BUBBLE-IMPL-001: implementation research for conservative common-flux momentum

## Question

The rising-bubble RCA identified a theoretical failure, not a parameter
failure: phase transport changes the density metric, while the production
momentum route advances velocity and pressure-acceleration histories in a
different metric.  The remedy selected in
`CHK-RA-CH14-BUBBLE-REMEDY-001` is to make the numerical state
`(psi, M, P)` and to transport `M` and `P` with exactly the same discrete map
that transports `psi`.

This note studies how to implement that theorem in the current code without
turning it into a benchmark branch, a damping patch, or a pressure/velocity
cap.

## Current code facts

The current implementation already has the right architectural seams, but they
are not yet connected to the theorem.

1. The interface transport face flux is formed in
   `src/twophase/levelset/fccd_advection.py:174`.

   ```text
   psi_face = self._fccd.face_value(q, axis)
   flux_face = psi_face * face_velocity
   total = total - self._fccd.face_divergence(flux_face, axis)
   ```

   This is the source of truth for the phase flux.  A valid momentum transport
   cannot reconstruct a different phase or mass flux later.

2. `PsiDirectTransport.advance_with_face_velocity` in
   `src/twophase/levelset/transport_strategy.py:392` currently returns only
   `psi`.  It records before/after reinitialization fields, but not the stage
   fluxes or post-stage projections that caused the change.

3. `TwoPhaseNSSolver._advance_interface_stage` calls
   `advance_with_face_velocity` in `src/twophase/simulation/ns_pipeline.py:785`.
   This is the correct point to request and attach a transport ledger to
   `NSStepState`.

4. `compute_ns_predictor_stage` in
   `src/twophase/simulation/ns_step_services.py:425` computes a velocity-form
   convective acceleration.  The IMEX-BDF2 path then uses previous velocities
   and previous convective accelerations in
   `src/twophase/simulation/ns_step_services.py:482`.  This is the route that
   must be bypassed or replaced for the conservative momentum form.

5. The affine pressure-jump path stores full face acceleration cochains:
   `state.pressure_accel_face_components` is assigned in
   `src/twophase/simulation/ns_step_services.py:1025` and carried through
   `src/twophase/simulation/ns_pipeline.py:994`.  The pre-blow-up audit showed
   this object growing from physical `O(10^3)` pressure jumps into `O(10^12)`
   face accelerations.  A conservative implementation must not let this
   history act as an unaccounted body force.

6. The configuration parser already validates `numerics.momentum.form`, but
   `src/twophase/simulation/config_constants.py:132` currently admits only
   `primitive_velocity`.  This is the natural UX switch for the new route.

## Implementation invariant

The implementation must preserve the following object identity:

```text
phase transport map == mass transport map == momentum transport map carrier
```

In code terms, the transport stage must produce a ledger, and every consumer
must use that ledger rather than rebuilding equivalent-looking fluxes.

The conserved variables are

```text
M_i = V_i * (rho_g + (rho_l - rho_g) psi_i),
P_i = M_i u_i.
```

For a face-flux stage in the units expected by `face_divergence`,

```text
F_M = rho_g F_V + (rho_l - rho_g) F_psi.
```

`F_V` is the volume flux induced by the same face velocity and `F_psi` is the
phase flux already used by the interface update.  The exact metric factors
must stay inside the existing FCCD/divergence operators; the ledger should not
duplicate geometric scaling in a separate convention.

## Stage coupling for TVD-RK3

The interface equation is advanced by Shu-Osher TVD-RK3:

```text
q1 = P(q0 + dt L(q0))
q2 = P(3/4 q0 + 1/4 (q1 + dt L(q1)))
q3 = P(1/3 q0 + 2/3 (q2 + dt L(q2))).
```

The common-flux theorem is not satisfied by storing only a single endpoint
flux.  Momentum must follow the same stage algebra:

```text
(M1,P1) = P0_FE(M0,P0; F0)
(M2,P2) = C_3/4,1/4((M0,P0), P0_FE(M1,P1; F1))
(M3,P3) = C_1/3,2/3((M0,P0), P0_FE(M2,P2; F2)).
```

Each forward-Euler substep must be a common-flux conservative remap, and each
Shu-Osher convex combination must mix `M` and `P` together.  The kinetic energy
inequality follows from the convexity of `|P|^2 / M`.

Therefore the ledger must be stage-native:

```text
TransportStageLedger {
  stage_kind,                 # FE or convex-combination stage
  convex_weights,
  face_volume_fluxes,
  face_phase_fluxes,
  face_mass_fluxes,
  reconstruction_certificate,
  post_stage_projection,
}

TransportLedger {
  dt,
  cell_volumes,
  stages,
  psi_before,
  psi_after_transport,
  psi_after_reinit,
  diagnostics,
}
```

The existing post-stage clipping and diffuse mass correction are dangerous for
the theorem if they are applied only to `psi`.  In conservative mode, every
post-stage projection must either provide an equivalent `(psi,M,P)` remap or
fail-close.

## Conservative momentum transport service

Add a service owned by the simulation layer, not by the pressure solver:

```text
src/twophase/simulation/conservative_transport.py

ConservativeMomentumTransport.advance(
    mass,
    momentum_components,
    velocity_components,
    transport_ledger,
    *,
    rho_l,
    rho_g,
    boundary_contract,
) -> ConservativeTransportResult
```

The result should include:

```text
mass_after
momentum_after_components
velocity_after_components
kinetic_energy_before
kinetic_energy_after
energy_delta
positivity_min_mass
certificate_status
```

The first certified anchor is a donor or more generally nonnegative remap
using the same mass flux.  High-order UCCD/FCCD face states are admissible only
as correction fluxes:

```text
F_P = F_P_anchor + theta (F_P_high - F_P_anchor),  0 <= theta <= 1,
```

where `theta` is computed from positivity and kinetic-energy inequalities.
This is not a tuning limiter; it is the proof object that allows high-order
accuracy without losing the energy theorem.

## Pressure-history change

For `momentum.form: conservative_common_flux`, the production route should not
carry `previous_pressure_accel_face_components` into the next predictor RHS.
The pressure stage must be treated as the constrained minimization

```text
u^{n+1} = argmin_{D u = 0, BC} 1/2 ||u - u*||^2_Mf.
```

Implementation consequence:

1. Keep scalar pressure/base-pressure history if needed for warm starts or
   diagnostics.
2. Recompute face pressure gradients from current scalar pressure, current
   density, current interface geometry, and the current capillary jump.
3. Reject any stored face cochain unless it is proved to be an exact current
   gradient representative and has zero pressure work against admissible
   divergence-free face velocities.

This directly targets the audited failure loop where a pressure face history
became an unaccounted acceleration.

## Reinitialization contract

Ridge-eikonal reinitialization changes `psi`; therefore it changes `M`.  In
conservative mode, reinitialization cannot remain a shape-only edit.

Valid options are:

1. The reinitializer returns a pseudo-time flux ledger `F_psi^R`, from which
   `F_M^R` and momentum remap are constructed.
2. A conservative remap is reconstructed from `delta psi` by solving
   `D F_psi^R = psi_before_reinit - psi_after_reinit`, with boundary fluxes
   constrained by the physical boundary contract and with an energy
   certificate for `P`.
3. The step fail-closes if reinitialization changes mass in a way that cannot
   be represented by a certified remap.

Velocity-preserving rescaling

```text
P_after = (M_after / M_before) P_before
```

is not automatically acceptable: if local mass increases, kinetic energy can
increase without physical work.  It may be used only if wrapped in the same
energy gate.

## UX proposal

Use the existing `numerics.momentum.form` path as the top-level declaration:

```yaml
numerics:
  momentum:
    form: conservative_common_flux
    transport:
      ledger: interface_stage_flux
      stage_coupling: ssp_rk3_common_flux
      anchor_flux: donor_common_flux
      high_order_correction: entropy_limited_uccd6
      positivity: fail_close
      kinetic_energy: fail_close
    history:
      variables: mass_momentum
      pressure_face_acceleration: forbidden
  interface:
    transport:
      spatial: fccd_flux
      time_integrator: tvd_rk3
      ledger: required
    reinitialization:
      conservative_remap: required
      unledgered_policy: fail_close
```

Parser changes:

1. Extend `_MOMENTUM_FORMS` with `conservative_common_flux`.
2. Add `RunConfig.momentum_form` because the parser currently validates the
   field but does not expose it as an explicit runtime option.
3. Add conservative transport options with strict defaults.
4. Reject incompatible combinations early:
   - `conservative_common_flux` with unledgered reinitialization.
   - `conservative_common_flux` with velocity-form `imex_bdf2` history.
   - `pressure_face_acceleration != forbidden` unless a work certificate is
     implemented.

This UX keeps primitive velocity available for old experiments, while making
the new theorem an explicit contract rather than a hidden special case.

## Time integration decision

The current `imex_bdf2` + `implicit_bdf2` route is not theorem-compatible in
velocity variables when `rho` changes.  There are two mathematically valid
implementation choices.

1. Implement the conservative geometric split first:

   ```text
   common-flux transport of (M,P)
   -> physical impulses in the current mass metric
   -> pressure projection in the current face mass metric
   ```

   This avoids false BDF2 stability claims and is the smallest route that
   tests the identified cause.

2. Implement variable-mass BDF2 only after transported history states exist:

   ```text
   (M^n,P^n)     transported to the n+1 mass coordinates
   (M^{n-1},P^{n-1}) transported to the n+1 mass coordinates
   ```

   Only then can a BDF2 identity be written without unaccounted mass-mismatch
   terms.

The implementation should choose the first route as the proof anchor and keep
the second as the path for restoring higher-order physical-time integration.
Calling the old velocity BDF2 from the conservative route would reintroduce the
same bug in a new wrapper.

## CCD/FCCD/UCCD connection

The scheme should not branch on "bubble" or on a chosen visual outcome.  It
should separate responsibilities:

1. FCCD owns the phase flux ledger and the pressure/operator adjoint pair.
2. UCCD6 may provide high-order correction fluxes, but only behind the
   entropy/positivity gate.
3. DCCD may be used as a dissipative anchor or remap component when the
   resulting operator is explicitly part of the common-flux theorem.
4. None of CCD/FCCD/UCCD should be used as a hidden pressure or velocity
   suppressor.

This keeps the remedy orthogonal to the CCD family: the theorem constrains the
transport map, while the CCD variants supply reconstructions and operators.

## Code-change dependency order

1. Add ledger dataclasses and diagnostics.

   Target files:
   - `src/twophase/levelset/transport_ledger.py`
   - `src/twophase/simulation/ns_step_state.py`

2. Extend `FCCDLevelSetAdvection.advance_with_face_velocity` with
   `return_ledger=False`.  Default behavior must remain byte-for-byte
   compatible for old callers.  In ledger mode, the TVD-RK3 stages must be
   expanded explicitly rather than hidden inside `tvd_rk3`.

3. Extend `PsiDirectTransport.advance_with_face_velocity` to store
   `last_transport_ledger` and, when requested, return `(psi, ledger)`.
   Reinit and mass-correction events must be included as ledger events, not
   silently applied after the fact.

4. Add `ConservativeMomentumTransport` and tests for closed, wall, and
   periodic boundaries on nonuniform grids.

5. Route `NSStepState` through conservative variables when
   `momentum.form == conservative_common_flux`.
   `compute_ns_predictor_stage` must skip the velocity-form convective
   acceleration and consume the conservative transport result instead.

6. Disable face pressure-acceleration history in the conservative route.
   Scalar pressure warm starts may remain.

7. Add checkpoint fields for all state that affects restart equivalence:
   current `M`, `P`, scalar pressure histories, conservative transport
   histories, reinit monitors, and any variable-mass history states.  Restart
   equality must be tested by comparing zero-start and restart trajectories.

8. Only after the anchor passes, add high-order correction fluxes and the
   entropy limiter.

## Verification gates

The following tests should be added before trusting a rising-bubble run.

1. `test_transport_ledger_matches_psi_endpoint`

   Reapply the recorded ledger divergence to `psi_before` and recover
   `psi_after_transport` to roundoff.

2. `test_ssp_rk3_common_flux_energy_gate`

   Use the recorded RK stages to update `(M,P)` and verify

   ```text
   K_after <= K_before + epsilon.
   ```

3. `test_post_stage_projection_requires_remap`

   Enable clipping or mass correction without a remap certificate and assert a
   fail-close in conservative mode.

4. `test_nonuniform_grid_common_flux`

   Repeat the energy gate on the `32 x 64`, `10mm x 20mm` rising-bubble grid
   with wall and periodic boundaries.

5. `test_pressure_history_forbidden_in_conservative_mode`

   Assert that `previous_pressure_accel_face_components` is absent from the
   conservative predictor/PPE RHS route.

6. `test_restart_conservative_state_roundtrip`

   Save the previous-step state and restart from it; verify that zero-start and
   restart agree before the known blow-up window.  This directly protects the
   checkpoint issue found earlier.

7. `test_reinit_requires_conservative_remap`

   Trigger ridge-eikonal reinitialization and assert either a valid remap
   certificate or a fail-close.  Silent `psi`-only reinit is not allowed.

8. Integration gate:

   Run rising bubble on `N=32 x 64`, `10mm x 20mm`, physical water-air
   parameters, and track the separate budgets:

   ```text
   transport energy defect
   reinit remap defect
   capillary work defect
   gravity work
   pressure projection defect
   total mechanical energy defect
   ```

## Expected implementation risk

The main risk is not syntax or GPU plumbing; it is accidentally preserving the
old bug under a new name.  The high-risk points are:

1. Letting `psi` clipping or mass correction alter density without a momentum
   remap.
2. Calling the old velocity-form `imex_bdf2` predictor after common-flux
   transport.
3. Keeping face pressure-acceleration history as a hidden force.
4. Treating an FCCD high-order face value as automatically entropy stable.
5. Saving checkpoints without all mass/momentum/history variables needed for
   exact restart.

The implementation should fail-close at each of these points.  Passing by
silence would be worse than stopping early, because the observed production
failure was exactly a silent energy injection.

## Final implementation judgement

The correct implementation route is:

```text
primitive velocity route remains legacy
conservative_common_flux route becomes the theorem-bearing production route
```

The first code target should be the stage-native transport ledger.  Once that
exists, the rest of the scheme can be expressed as consumers of the same
discrete transport map.  Without that ledger, any momentum or pressure patch is
still guessing at the physical map after the fact.
