# CHK-RA-CH14-BUBBLE-REMEDY-THEORY-001: theory-first remedies for rising-bubble blow-up

## Question

The 10 mm x 20 mm water-air rising-bubble run on a 32 x 64 grid is stable to
`T=0.01`, but the continuation fails near `t=0.018033 s`.  The root-cause
analysis identified a near-Nyquist horizontal velocity mode localized in the
interface band.  This note derives countermeasures from the discrete physics.
It deliberately rejects fixes that only attenuate the symptom.

## Invariant Starting Point

The physical problem is not singular at the observed scale.  With a bubble
diameter of `D=5 mm`,

```text
Eo = (rho_l-rho_g) g D^2 / sigma = 3.402
t_sigma = sqrt(rho_l R^3 / sigma) = 1.473e-02 s
sqrt(gD) = 2.215e-01 m/s
Delta p_hydrostatic over 20 mm = 1.960e+02 Pa
Delta p_laplace = sigma/R = 2.880e+01 Pa
```

The pre-blowup state instead has

```text
max speed        = 1.559372e+04 m/s
max |pressure|   = 1.946613e+11 Pa
Nyquist energy fraction = 9.991236e-01
```

Any remedy must therefore explain how the discrete scheme prevents unphysical
energy transfer into interface-grid modes.  A smaller CFL, stronger damping, or
visual smoothing does not answer that question.

## State Variables

The remedy must promote the state from primitive velocity to conservative
variables:

```text
q_i       : liquid volume fraction in cell i
m_i(q)   = V_i (rho_g + (rho_l-rho_g) q_i)
p_i      = m_i u_i
```

The discrete total energy is

```text
E_h(q,m,p) = K_h(m,p) + sigma S_h(q) + Phi_h(m)
K_h(m,p)   = sum_i |p_i|^2 / (2 m_i)
Phi_h(m)   = sum_i m_i g y_i
```

On a staggered implementation the same structure is represented on face mass
and face momentum, but the metric is still the mass metric.  The important point
is not the storage location; it is that every transport, force, and projection
operator sees the same transported mass.

## Admissibility Theorem

A production rising-bubble step is admissible only if it can be decomposed as

```text
(q^n,m^n,p^n)
  -> transport by a common flux ledger
  -> conservative reinitialization/remap, or fail-close
  -> variational capillary, gravity, and viscous impulse
  -> mass-metric pressure projection
  -> certified checkpoint
```

and if each substep satisfies its own discrete work identity or inequality.
The theorem is intentionally stronger than "the run is stable".  Stability
without the identities can hide the same grid mode until another configuration
excites it.

## Transport Requirement

Let `F_q` be the phase flux produced by the interface transport scheme.  The
mass flux must be

```text
F_m = rho_g F_V + (rho_l-rho_g) F_q
```

where `F_V` is the geometric volume flux associated with the same face and
stage.  Momentum must be transported by the same mass flux:

```text
F_p = F_m u_up
q^T = q^n - dt D F_q
m^T = m^n - dt D F_m
p^T = p^n - dt D F_p
```

For multi-stage FCCD/UCCD updates the identity must hold stage-by-stage, not
only at the endpoint.  The ledger must record the face fluxes and the stage
weights used by the phase update.  The momentum update is not allowed to invent
a different advective stencil after the phase has moved.

For pure transport, an admissible discretization must satisfy

```text
K_h(m^T,p^T) <= K_h(m^n,p^n) + eps_T
```

with an explicitly reported defect `eps_T`.  A high-frequency mode can grow
only if some operator feeds kinetic energy into it; this inequality turns that
question into a measured certificate instead of a visual judgment.

## Reinitialization and Remap

Level-set reinitialization is not a harmless geometric postprocess in this
problem.  It changes `q`, therefore it changes mass.  A q-only reinitialization
followed by unchanged primitive velocity violates the conservative state:

```text
m = V rho(q) changes, but p = m u is not remapped by the same map.
```

The admissible retraction is a map

```text
R_h : (q^T,m^T,p^T) -> (q^R,m^R,p^R)
```

with the following contract:

```text
m_i^R = V_i (rho_g + (rho_l-rho_g) q_i^R)
sum_i V_i q_i^R = sum_i V_i q_i^T          up to a declared tolerance
sum_i p_i^R     = sum_i p_i^T              up to boundary/work terms
K_h(m^R,p^R) <= K_h(m^T,p^T) + eps_R
```

If this map cannot be constructed for the chosen reinitialization, the correct
production behavior is fail-close.  It is not acceptable to continue with a
profile-corrected interface and an inconsistent momentum field.

## Capillary Force

The capillary impulse must be the transport-adjoint Riesz representative of the
surface-energy variation.  In abstract form,

```text
delta S_h(q)[delta q] = <d_q S_h, delta q>
delta q = -dt D_q(u)
f_sigma = - sigma T_q(q)^* d_q S_h
```

where `T_q(q)` maps velocity to the induced phase transport and `T_q(q)^*` is
the adjoint taken in the same mass metric as the momentum equation.  This is the
only admissible way to decide which velocity modes capillarity can drive.

The pressure or component reaction space may be removed from the capillary
drive only as a reaction decomposition:

```text
X = [ range(M_f^{-1} D_f^T), component constraints ]
h_sigma = (I - Pi_X^M) f_sigma
```

This is not the old blanket replacement `c_sigma -> Pi_R c_sigma`.  That
replacement destroyed the oscillating droplet by algebraically setting the
release acceleration to zero.  Here the full variational force is constructed
first, and only null-work reaction components are separated in the correct mass
metric.

## Gravity

Gravity must be coupled through the potential energy

```text
Phi_h(m) = sum_i m_i g y_i
```

The body impulse is the negative gradient of this potential in the same
conservative variables:

```text
f_g = - d_m Phi_h
```

For the rising bubble, buoyancy is not an independent forcing that can be
patched onto a primitive velocity equation after density transport.  It is the
difference between transported mass and the gravitational potential.  The work
ledger must therefore report

```text
Delta K + Delta Phi
```

for the gravity substep.  This prevents an interface-density mismatch from
appearing as artificial kinetic energy.

## Viscosity

The viscous step is admissible if its discrete stress operator is dissipative:

```text
<u, L_mu(q) u> <= 0
```

in the current mass/face metric and with the configured boundary conditions.
CCD, FCCD, and UCCD ingredients may be used to build the operator, but the
acceptance criterion is the work inequality, not the operator name.  A
defect-correction solve is valid only if the residual defect is small enough
that the certified viscous work remains non-positive within tolerance.

## Pressure Projection

The pressure step must be a mass-metric constrained minimization:

```text
u^{n+1} = argmin_{D u = 0, BC} 1/2 ||u - u^*||^2_{M_f}
```

Equivalently,

```text
M_f (u^{n+1} - u^*) + G p = 0
D u^{n+1} = 0
```

This gives

```text
K(M_f,u^{n+1}) <= K(M_f,u^*)
```

for the projection.  The pressure gauge is a Lagrange multiplier; it is not the
primary physical state.  Affine pressure history must therefore be stored and
restarted as the same face impulse/cochain used by the conservative state, not
as a scalar field that is later reinterpreted with another metric.

## Candidate Remedies and Verdicts

### R01: Reduce CFL

Rejected as a solution.  The failed run collapses because velocity grows to an
unphysical value.  Smaller `dt` may delay the visible blow-up, but it does not
establish a bound on high-frequency kinetic-energy production.

### R02: Add DCCD/UCCD damping

Rejected as a primary remedy.  DCCD/UCCD can be part of a conservative or
dissipative operator, but using them to suppress the observed ring or Nyquist
mode would be a filter.  The theory requires proving where the filtered energy
went.  Without a work identity, this is symptom management.

### R03: Curvature cap or smoothing

Rejected.  The blow-up signature is velocity/pressure-energy injection, not a
physical curvature singularity.  Curvature modifications also alter the surface
energy without a corresponding variational derivation.

### R04: Pressure smoothing or scalar pressure fallback

Rejected.  The PPE appears to solve the large RHS it is given.  Smoothing the
pressure hides the inconsistent RHS but does not repair mass-momentum
compatibility or the pressure projection metric.

### R05: Disable affine pressure history

Rejected as a solution.  Affine history may amplify the inconsistency, but it is
not inherently unphysical.  The correct condition is that affine history be
stored in the same cochain and metric as the pressure projection.  Turning it
off would not prove the remaining scheme.

### R06: Turn off reinitialization

Rejected as a general remedy.  It can isolate reinitialization as a cause in a
probe, but long runs need a controlled profile/geometry map.  The acceptable
answer is conservative remap or fail-close.

### R07: Use range projection of capillarity as production force

Rejected.  Prior oscillating-droplet verification showed that production
replacement by a projected capillary cochain can eliminate the physical
oscillation.  Projection is a diagnostic or reaction-space decomposition, not a
force replacement.

### R08: Conservative common-flux transport of phase, mass, and momentum

Accepted as necessary.  It is the minimal structure that prevents the interface
from moving on one flux while density and momentum move on another.  It directly
targets the observed interface-band mode.

### R09: Conservative reinitialization/remap of `(q,m,p)`

Accepted as necessary.  Without it, reinitialization can break the conservative
state after every step.  This is especially dangerous at water-air density
ratio because a small phase displacement changes mass strongly.

### R10: Mass-metric pressure projection and pressure-history cochain

Accepted as necessary.  Projection must remove divergence by an orthogonal
operation in the metric of the transported mass.  Pressure history must be
stored as the corresponding impulse/cochain.

### R11: Variational capillary and gravity impulses

Accepted as necessary.  These are the only force definitions that make energy
exchange auditable.  They also generalize to non-elliptic and non-static
interfaces, avoiding benchmark-specific logic.

### R12: High-k energy monitor

Accepted as diagnostic and fail-close gate, not as a remedy.  The monitor can
identify when a theorem condition failed, but it must not silently filter the
state.

## CCD, FCCD, UCCD Connectivity

The remedy is compatible with the CCD family, but only with clear roles:

```text
FCCD : phase and geometric flux ledger, pressure/divergence incidence
UCCD : optional high-order conservative flux evaluator for momentum transport
CCD  : viscous/stress and elliptic operators when work identities hold
DCCD : diagnostic or theorem-derived projection, not ad hoc damping
```

The decisive requirement is orthogonality of contracts, not orthogonality of
code names:

```text
transport       -> conservative common flux
capillarity     -> surface-energy variation
gravity         -> potential-energy variation
viscosity       -> dissipative stress
pressure        -> mass-metric constraint projection
reinitialization-> conservative remap or fail-close
```

Each operator may use CCD/FCCD/UCCD discretization, but no operator may consume
a state whose conservative variables were produced by another incompatible
flux.

## YAML and UX Contract

The production YAML should expose the mathematical contract, not implementation
switches that invite invalid mixtures.  A suitable user-facing shape is:

```yaml
run:
  momentum_form: conservative_common_flux

numerics:
  conservative_transport:
    strict: true
    energy_certificate: strict
    high_k_monitor: fail_close
  pressure:
    projection_metric: transported_face_mass
    history_storage: face_impulse_cochain
  capillary:
    force_form: surface_energy_adjoint
    reaction_projection: diagnostic_or_constraint
  reinitialization:
    remap: conservative_qmp_or_fail
```

Invalid combinations should fail during config validation:

```text
momentum_form: conservative_common_flux
  requires conservative q,m,p restart state
  requires common flux ledger from interface transport
  requires pressure metric = transported_face_mass
  forbids q-only reinitialization in production
  forbids silent clipping/filtering/damping of velocity or pressure
```

This keeps the user from selecting a physically meaningful label while still
running the primitive-velocity pathway.

## Implementation Dependency Order

The implementation should be ordered by mathematical dependency:

1. Promote the full NS state to `(q,m,p)` or its face-compatible equivalent.
2. Route phase, mass, and momentum through the existing FCCD flux ledger.
3. Store restart/checkpoint state before each step with all variables needed to
   reproduce the next update.
4. Replace q-only reinitialization in production with conservative remap, or
   fail-close when the remap certificate cannot be produced.
5. Express capillary and gravity forces as energy variations of `S_h(q)` and
   `Phi_h(m)`.
6. Apply viscosity only through a certified dissipative stress operator.
7. Apply pressure projection as a transported-mass-metric minimization.
8. Emit a per-step ledger:

```text
Delta K_transport
Delta K_reinit
Delta K_capillary + sigma Delta S
Delta K_gravity + Delta Phi
viscous_work
Delta K_projection
high_k_energy_fraction
certificate_status
```

Fail-close is part of the scheme, not an emergency workaround.  If a step
cannot produce the ledger, the state is not a theorem-grade production state.

## Decision

The theoretically justified countermeasure is not DCCD suppression of velocity
or pressure.  It is a conservative common-flux Navier-Stokes route with:

```text
common flux transport of q,m,p
conservative reinitialization/remap or fail-close
variational capillary and gravity impulses
dissipative viscosity certificate
transported-mass pressure projection
face-cochain pressure history
per-step energy and high-k certificates
```

This directly addresses the observed failure mechanism.  The interface-band
Nyquist mode is no longer treated as something to damp after it appears; the
scheme is required to identify which operator injected its energy, and to reject
the step if no admissible discrete work identity supports that injection.
