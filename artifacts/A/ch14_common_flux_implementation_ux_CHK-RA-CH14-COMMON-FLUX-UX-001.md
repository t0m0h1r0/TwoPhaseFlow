# CHK-RA-CH14-COMMON-FLUX-UX-001: implementation method and YAML UX for conservative common-flux route

## Question

Define how to implement the conservative common-flux remedy and how to expose it
in YAML without allowing physically invalid mixtures.  This note is a design
contract, not a code patch.  The current production runtime correctly
fail-closes `momentum.form: conservative_common_flux` until the full route is
wired.

## Existing Boundary

The repository already has the first safe slice:

```text
src/twophase/levelset/transport_ledger.py
src/twophase/levelset/fccd_advection.py
src/twophase/simulation/conservative_transport.py
```

`FCCDLevelSetAdvection.advance_with_face_velocity(..., return_ledger=True)`
records phase fluxes and face-volume fluxes.  `ConservativeCommonFluxTransport`
then reconstructs

```text
F_m = rho_g F_V + (rho_l-rho_g) F_q,
F_p = F_m u_up.
```

It already rejects clipped, mass-corrected, or post-stage-projected ledgers.
This is the correct fail-close posture.

The full NS route is not wired.  `normalise_ns_scheme_runtime` still raises
`NotImplementedError` for `conservative_common_flux`.  This must remain true
until the state, remap, projection metric, pressure history, checkpoint, and
energy certificates all consume the same conservative state.

## Implementation Dependency Order

### G0: Config Contract And Fail-Close Validation

Add the YAML surface and parser fields first, but keep runtime fail-close unless
all required subcontracts are present.  The validator must reject invalid
mixtures before the solver is built.

Required checks:

```text
momentum.form == conservative_common_flux
  requires interface transport = FCCD face flux with ledger
  forbids phase clipping/mass correction as hidden post-stage projection
  requires reinit remap = conservative_qmp_or_fail
  requires grid rebuild remap = conservative_qmp_or_fail if grid rebuilds
  requires projection metric = transported_face_mass
  requires pressure history = face_impulse_cochain
  requires checkpoint state = pre_step_qmp for restartable runs
  forbids silent damping/filtering/velocity clipping/pressure smoothing
```

This gate is an implementation safety feature.  It is not a numerical fix.

### G1: Conservative State Container

Introduce a state object near `ns_step_state.py` or a new
`simulation/conservative_state.py`:

```text
ConservativeState:
  q
  density
  momentum_components
  velocity_components
  face_mass_components or face_metric
  grid_hash
```

Construction:

```text
density = rho_g + (rho_l-rho_g) q
momentum_components = density * velocity_components
velocity_components = momentum_components / density
```

For face projection, compute the metric by the same face locus as pressure and
transport:

```text
rho_f = rho_g + (rho_l-rho_g) P_f q
M_f   = face_measure * rho_f
```

The face metric must not be recomputed by an unrelated interpolation inside the
pressure solver.

### G2: Interface Stage Owns The Common Flux Ledger

Modify `_advance_interface_stage` only for the conservative route:

```text
q_T, ledger = advance_with_face_velocity(
    q^n,
    projected_face_velocity,
    dt,
    clip_bounds=None,
    return_ledger=True,
)
```

Then immediately run common-flux transport:

```text
(m_T,p_T,u_T), cert_T = ConservativeCommonFluxTransport.advance(
    density=m^n/V,
    momentum_components=p^n/V,
    ledger=ledger,
    rho_l=rho_l,
    rho_g=rho_g,
)
```

The step state receives:

```text
state.psi = q_T
state.rho = rho_T
state.u, state.v = u_T
state.transport_ledger = ledger
state.conservative_transport_certificate = cert_T
```

No clipping is allowed here.  If `q_T` leaves the admissible interval beyond a
declared tolerance, the next admissible operation is a conservative remap or a
fail-close.

### G3: Conservative Reinit/Grid-Remap

The existing `rebuild_ns_grid` remaps `psi,u,v` and mass-corrects `psi`.  That
is invalid for this route because it does not remap `(q,m,p)` by one map.

Add a separate conservative remap interface:

```text
ConservativeQMPRemapper.remap(state, old_grid, new_grid, projection_info)
  -> state_R, certificate_R
```

Certificate:

```text
m_R = V rho(q_R)
sum V q_R = sum V q_T + eps_V
sum p_R   = sum p_T   + eps_P
K_R - K_T = eps_R
```

Until this exists, any conservative route with scheduled reinitialization or
grid rebuild must fail closed.  A diagnostic no-reinit/no-rebuild probe may be
allowed only if YAML marks it as diagnostic, not production.

### G4: Force And Predictor Bridge

Existing force code can remain velocity-facing only if velocity is treated as a
view:

```text
u = p / m
```

After each force impulse, write back to momentum:

```text
p* = M_f(q_R) u*
```

Capillary must use the surface-energy adjoint route already formalized in
SP-AI/SP-AJ.  Gravity must be charged against `Phi_h(m)`.  Viscosity must emit a
signed work certificate.  If a legacy operator cannot report work in the
transported metric, it may be kept on the primitive route only.

### G5: Transported-Mass Projection

Add or adapt a pressure projection service that receives `M_f(q_R)` explicitly:

```text
u^{n+1} = argmin_{D u = 0, BC} 1/2 ||u-u*||^2_{M_f(q_R)}.
```

Pressure history must be stored as face impulse/cochain components in the same
metric:

```text
solver/p_prev_accel_face_components
```

Scalar pressure is an output representative only after the Hodge/integrability
diagnostic passes.

### G6: Energy And High-K Ledger

Introduce an `EnergyLedger` with device-native intermediate arrays and explicit
host scalar extraction only at the diagnostics boundary:

```text
transport_delta_K
remap_delta_K
capillary_delta_K_plus_sigma_delta_S
gravity_delta_K_plus_delta_Phi
viscous_work
projection_delta_K
high_k_interface_fraction
certificate_status
```

The high-k monitor is never a filter.  It should initially use GPU-native
stencil/high-pass diagnostics on the interface band.  Host FFT can be a plot or
offline diagnostic, not the production gate.

### G7: Checkpoint Schema

Bump the checkpoint schema for this route.  Store all variables needed to
reproduce the next step:

```text
state/psi
state/density
state/momentum_components/0
state/momentum_components/1
state/u
state/v
state/p
solver/p_prev_accel_face_components/*
solver/projected_face_components/*
solver/conservative_energy_ledger/*
manifest:
  momentum_form = conservative_common_flux
  conservative_state_schema = qmp_v1
  state_phase = pre_step
```

Primitive checkpoints must not be accepted as conservative restarts.  A
conservative checkpoint may include `u,v` for convenience, but restart
authority belongs to `(q,m,p)` and the face-history cochains.

## YAML UX

### Canonical Production Form

Use `numerics.momentum.form` as the canonical location.  Keep
`run.momentum_form` as a legacy alias only when it agrees.

```yaml
numerics:
  momentum:
    form: conservative_common_flux
    conservative_common_flux:
      mode: strict
      state: cell_qmp
      transport:
        ledger: required
        phase_stage_projection: forbidden
        energy_gate: fail_close
      remap:
        policy: conservative_qmp_or_fail
        allow_q_only: false
      certificates:
        energy: strict
        high_k_interface: fail_close
      tolerances:
        mass_consistency_rel: 1.0e-12
        momentum_consistency_rel: 1.0e-10
        transport_energy_abs: 1.0e-10
        remap_energy_abs: 1.0e-10
        projection_energy_abs: 1.0e-10
        high_k_growth_rel: 1.0e-2

  interface:
    transport:
      variable: psi
      spatial: fccd
      time_integrator: tvd_rk3
      ledger: required
      clipping: forbidden

  projection:
    metric: transported_face_mass
    pressure_history: face_impulse_cochain
    face_flux_projection: true
    canonical_face_state: true
    face_native_predictor_state: true
```

Reinitialization should live in the existing interface section:

```yaml
interface:
  reinitialization:
    algorithm: ridge_eikonal
    schedule:
      every_steps: 1
    remap:
      policy: conservative_qmp_or_fail
      defect_ledger: required
```

Checkpoint UX should live under `output` because CLI flags already control
explicit checkpoint paths:

```yaml
output:
  checkpoints:
    state: pre_step_qmp
    include_energy_ledger: true
    include_face_history: true
```

### Diagnostic Escape Hatch

Diagnostic probes may temporarily run without a full remap only if they are
explicitly labelled:

```yaml
numerics:
  momentum:
    conservative_common_flux:
      mode: diagnostic_transport_only
```

This mode must not be accepted by production benchmark YAMLs.  It may run unit
or one-step probes and should emit a warning that reinit/grid rebuild is
disabled or fail-closed.

### Error Messages

The UX should teach the theorem when it rejects a config:

```text
conservative_common_flux requires interface.reinitialization.remap.policy=
conservative_qmp_or_fail because q-only reinit changes mass without remapping
momentum.
```

```text
conservative_common_flux cannot use grid.distribution.schedule=1 until
conservative grid remap of (q,m,p) is available.
```

```text
conservative_common_flux requires projection.metric=transported_face_mass;
primitive pressure metrics would make the projection energy certificate invalid.
```

## Test Plan

Unit tests:

```text
config parses canonical conservative_common_flux YAML
invalid conservative mixtures fail before solver construction
ledger path rejects clipping and mass correction
uniform velocity common-flux transport preserves velocity
q-only reinit is rejected
primitive checkpoint is rejected for conservative restart
conservative checkpoint round-trips q,m,p and face history
pressure projection manufactured case decreases M_f kinetic energy
high-k monitor reports without modifying velocity
```

Integrated gates:

```text
static droplet: no parasitic kinetic-energy injection
oscillating droplet N=32,T=1: physical release remains nonzero
capillary wave N=32, one period: no regression of phase/energy diagnostics
rising bubble N=32x64,T=0.01: no regression from current taste test
rising bubble continuation toward 0.02: failure, if any, must name a ledger term
```

## Decision

The implementation should be added as a strict parallel route, not as a mutation
of the primitive-velocity route.  The YAML should expose one coherent contract:

```text
conservative_common_flux = qmp state
                         + common flux ledger
                         + conservative remap/fail-close
                         + transported-mass projection
                         + face-history cochains
                         + energy/high-k certificates.
```

Any config that selects only part of this bundle must fail during validation.
