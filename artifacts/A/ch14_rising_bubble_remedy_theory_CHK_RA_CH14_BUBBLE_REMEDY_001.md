# CHK-RA-CH14-BUBBLE-REMEDY-001: theory of valid remedies

## Question

The rising-bubble RCA identified two coupled failures:

1. `rho` is moved by phase transport/reinitialization while velocity and
   momentum history are not moved by the same map.
2. The affine pressure-jump path stores full face acceleration cochains and
   feeds them back into the next predictor and PPE RHS.

This note derives what a valid remedy must prove.  It is not an implementation
patch.  It rejects damping, CFL-only reduction, pressure masking, curvature
smoothing, density clipping, benchmark branches, and arbitrary cochain caps as
remedies because they do not restore a conservation or energy theorem.

## Non-negotiable invariant

Let `M_i = rho_i V_i > 0` be cell or component-control-volume mass and
`P_i = M_i u_i` be momentum.  The kinetic energy is

```text
K(M,P) = sum_i 1/2 |P_i|^2 / M_i.
```

For pure advection, a valid scheme must satisfy either exact preservation by a
common volume-preserving map or, for upwind/remap schemes, a one-sided entropy
inequality

```text
K(M^{n+1},P^{n+1}) <= K(M^n,P^n).
```

This is not optional.  The function `|P|^2/M` is the perspective of a convex
quadratic, so any conservative update that mixes mass and momentum with the
same nonnegative weights is kinetic-energy non-increasing.  If mass and
momentum use different weights, no sign theorem exists.

The discrete theorem is metric-aware and therefore applies on nonuniform grids
when written in masses `M_i`, not just pointwise densities `rho_i`.

## Candidate remedies and theoretical status

### R0: reduce CFL

Rejected as a remedy.  Smaller time steps can delay the observed failure, but
they do not change the sign of the defective update.  The production audit
showed the advective time-step collapse happens after energy and PPE RHS have
already grown.  CFL is a detector, not a conservation law.

### R1: add damping or velocity/pressure suppression

Rejected.  Damping can hide energy injection by adding artificial dissipation,
but the injected term remains unaccounted.  It also changes the physical
Rayleigh-Lamb, capillary-wave, and rising-bubble dynamics.  It is not a
derivation from the water-air equations.

### R2: cap curvature, smooth curvature, or clip density

Rejected.  The production audit showed `capillary_jump_linf` stays `O(10^3)`
while `capillary_face_linf` and stored pressure-acceleration faces grow to
`O(10^12)`.  The immediate pathology is a face-cochain/history amplification,
not simply an extreme curvature value.  Smoothing may reduce the input but does
not repair the operator that amplifies it.

### R3: project or cap the stored face acceleration history

Rejected as a standalone remedy.  A projection/cap can prevent the largest
observed value, but it does not explain what physical work was removed.  It is
acceptable only as a fail-close diagnostic or as part of an energy projection
derived from a constrained minimization problem.

### R4: use DCCD/FCCD/UCCD as stronger filters

Rejected as stated.  DCCD/FCCD/UCCD are useful operators, but the invariant is
not "more filtering"; it is "same mass flux in phase and momentum."  DCCD or
UCCD may appear inside a certified flux reconstruction, but they cannot replace
the common-flux theorem.

### R5: conservative common-flux momentum transport

Supported.  This is the core remedy.

Let a phase transport stage provide a mass flux `F_M,f` through each oriented
face.  The momentum update must use the same mass flux:

```text
M_i^{T} = M_i^n - dt * sum_f D_if F_M,f,
P_i^{T} = P_i^n - dt * sum_f D_if (F_M,f u_f^donor).
```

For a donor-cell or more generally convex remap, the update is a convex mixture
of mass packets carrying their velocities, so Jensen's inequality gives

```text
K(M^T,P^T) <= K(M^n,P^n).
```

This directly targets the identified failure.  The face mass flux must be the
same object induced by `psi` transport:

```text
F_M = rho_g F_V + (rho_l-rho_g) F_psi,
```

where `F_V` is the volume flux and `F_psi` is the phase flux.  If the projected
face velocity is discretely divergence-free, the constant-density part is
conservative; on walls, impermeable boundary faces carry zero normal mass flux.

### R6: high-order common-flux reconstruction

Supported only with an entropy certificate.  A high-order UCCD/FCCD
reconstruction may replace donor-cell face velocity only if it preserves:

```text
M_i^{T} > 0,
K(M^T,P^T) <= K(M^n,P^n) + epsilon_transport.
```

The safe mathematical structure is a flux-corrected or entropy-limited
high-order flux:

```text
F_P = F_P^{anchor} + theta (F_P^{high} - F_P^{anchor}),  0 <= theta <= 1,
```

where the anchor is the common-flux convex update and `theta` is chosen from the
energy/positivity inequalities, not from a visual or benchmark tuning rule.
This is not arbitrary damping: the limiter is the proof mechanism.

### R7: BDF2 in velocity variables

Rejected in the current form.  Constant-mass BDF2 has a G-stability identity,
but the current step evaluates old velocities in the new density metric:

```text
M(rho^{n+1}) * (3u^{n+1}-4u^n+u^{n-1}) / (2dt).
```

When `M(rho^{n+1}) != M(rho^n)`, the usual G-stability identity has extra
mass-mismatch terms with no sign.  This matches the saved checkpoint, where the
BDF2 base state already contains `2.475x` the current kinetic energy.

### R8: variable-mass BDF2 with transported history

Supported as a later theorem, not as the first correction.  To make multistep
time integration valid, history states must be expressed in the same transported
mass coordinates:

```text
(M^{n -> n+1}, P^{n -> n+1})     = T_{n->n+1}(M^n, P^n),
(M^{n-1 -> n+1}, P^{n-1 -> n+1}) = T_{n-1->n+1}(M^{n-1}, P^{n-1}).
```

Only then may one form BDF2 on aligned velocities or momenta.  Without this
history transport, BDF2 is a source of nonphysical energy.

### R9: pressure projection as an M-orthogonal constrained minimization

Supported and required.  After transport and explicit physical forces, pressure
should be a Lagrange multiplier enforcing incompressibility:

```text
u^{n+1} = argmin_{D u = 0, BC} 1/2 ||u-u^*||_{M_f}^2.
```

The discrete pressure correction is then an `M_f`-orthogonal projection and
cannot increase kinetic energy.  This is the correct role of pressure.  A stored
face acceleration cochain is admissible only if it is the exact current
gradient representative of a scalar pressure increment in the same mass metric
and has zero pressure work against admissible velocities.

### R10: scalar pressure history instead of face acceleration history

Supported as a pressure-history remedy.  The production failure loop stores
`previous_pressure_accel_face_components` and adds its divergence to the next
PPE RHS.  This should be replaced by storing scalar pressure/base states and
recomputing exact current face gradients from current geometry and density.

If a face cochain is needed for affine-jump algebra, it must pass:

```text
integrability residual <= tolerance,
pressure work          = <a_p, u_divfree>_{M_f} ~= 0,
history energy budget  <= certified bound.
```

Otherwise the step must fail-close.  A non-integrable face cochain is not a
pressure history; it is an unaccounted force.

### R11: capillary force as a surface-energy discrete gradient

Supported and required.  Capillary work must be tied to surface energy:

```text
sigma (S^{n+1} - S^n) = -dt <a_sigma, u^{work}>_{M_f} + R_sigma,
```

with `R_sigma` bounded by a known discretization tolerance.  Pressure-jump and
closed-interface Riesz machinery may provide the cochain, but the accepted
cochain must satisfy the discrete-gradient work identity.  The production
symptom, where moderate `capillary_jump_linf` turns into enormous
`capillary_face_linf`, is exactly what this gate must prevent.

### R12: reinitialization as a conservative remap of `(psi, M, P)`

Supported and required.  Reinitialization changes `psi`, hence density.  If it
acts only on `psi`, it reintroduces the same mass-momentum mismatch after the
transport stage.  A valid reinitialization must produce a pseudo-time remap
flux `F_psi^R` such that

```text
psi^R = psi^T - D F_psi^R,
M^R   = M^T   - D F_M^R,
P^R   = P^T   - D (F_M^R u^donor).
```

The reinitialization remap should be zero-physical-work or
kinetic-energy-non-increasing.  If ridge-eikonal reinitialization cannot return
such a flux/certificate, the production route must fail-close for cases where
the induced density change is not negligible.

### R13: gravity and buoyancy in total energy

Supported.  Rising bubbles must gain kinetic energy from gravity.  Therefore
the diagnostic cannot demand monotone kinetic energy for the full problem.  It
must track total mechanical energy:

```text
E_total = K + sigma S + int rho g y dV.
```

With consistent mass transport, the change in gravitational potential energy is
computed from the same mass flux.  This separates physical buoyancy work from
unphysical transport/history work.

## Recommended mathematical scheme

The most coherent scheme is a conservative geometric split with one transport
ledger.

### 1. Phase transport returns a flux ledger

The phase transport should return not only `psi^{T}`, but also a transport
certificate:

```text
TransportLedger {
  dt,
  cell_volumes,
  face_volume_fluxes,
  face_phase_fluxes,
  face_mass_fluxes,
  donor_or_reconstruction_data,
  positivity_bounds,
  divergence_residual,
}
```

For the current code, the natural source is the FCCD face path around
`src/twophase/levelset/fccd_advection.py:174`, where `psi_face * face_velocity`
is already formed.

### 2. Momentum is updated as conservative `P = M u`

Momentum transport consumes exactly the ledger mass flux:

```text
M^T = M^n - dt D F_M,
P^T = P^n - dt D F_P(F_M,u),
u^T = P^T / M^T.
```

The first production version should use the theorem anchor.  High-order
corrections are allowed only under the energy/positivity certificate in R6.

### 3. Reinitialization returns a remap certificate

If `psi^T` is reinitialized to `psi^R`, the reinitializer must provide an
equivalent conservative remap for density and momentum.  The ledger may be a
geometric flux, a minimal-norm flux solving `D F = psi^T-psi^R`, or another
certified remap, but it must update `(psi,M,P)` consistently.

### 4. Forces are applied after mass alignment

After transport/reinit, the force stage works in the current mass metric.  A
simple energy-safe order is:

```text
(M^R,P^R) -> gravity/viscosity/capillary impulse -> pressure projection.
```

Viscosity should be dissipative in `M^R`.  Gravity is checked through total
energy.  Capillary force must satisfy the surface-energy discrete-gradient
identity.

### 5. Pressure is an orthogonal projection, not a stored acceleration loop

Pressure correction should be the `M_f`-orthogonal projection of face velocity.
The affine pressure-jump path may keep scalar pressure/jump state, but should
not feed an arbitrary previous face acceleration cochain back into the next
PPE RHS.  If a face cochain is retained internally, it must be recomputed from
current scalar variables and pass exact-gradient/work gates.

## CCD/FCCD/UCCD compatibility

The remedy is compatible with the CCD family if responsibilities are separated:

- FCCD owns the conservative face flux ledger for phase and mass.
- UCCD6 supplies high-order face states or correction fluxes only after the
  common-flux entropy condition is enforced.
- DCCD may provide controlled dissipation in reconstructions or reinit remaps,
  but it must not act as an ad hoc pressure/velocity suppressor.
- The pressure operator remains a variational adjoint pair; the projection
  theorem is written in the same face mass metric used by momentum.

This is more compatible with the present direction than replacing the stack with
an unrelated FD/WENO/PPE route.

## Required verification gates

The following gates should be passed before trusting a full rising-bubble run.

1. Pure common-flux transport:

```text
K(M^T,P^T) - K(M^n,P^n) <= epsilon_transport.
```

Already verified offline by `CHK-RA-CH14-BUBBLE-FLUX-001`.

2. Nonuniform-grid common-flux transport:

Same inequality using actual component-control-volume masses on the nonuniform
`32 x 64`, `10mm x 20mm` grid.

3. Reinitialization remap:

```text
K(M^R,P^R) - K(M^T,P^T) <= epsilon_reinit,
mass/phase constraints satisfied.
```

4. Pressure projection:

```text
K(M,u^{n+1}) <= K(M,u^*) + epsilon_projection,
D u^{n+1} ~= 0.
```

5. Capillary work:

```text
K^{after sigma}-K^{before sigma}
  + sigma(S^{after}-S^{before}) <= epsilon_sigma.
```

6. Gravity work:

```text
K + sigma S + int rho g y dV
```

changes only by viscosity and certified truncation error.

7. Production history gate:

`previous_pressure_accel_face_components` must be absent, scalar-exact, or
work-certified.  A growth pattern like `1e3 -> 1e12` is an immediate fail-close.

## Final judgement

The valid countermeasure is not a parameter adjustment.  It is to change the
state variable and update theorem:

```text
from: velocity plus acceleration histories in a changing density metric
to:   conservative mass and momentum transported by one certified flux ledger
```

Pressure and capillary terms then become constrained work/energy operators in
the aligned mass metric.  Reinitialization becomes a conservative remap, not a
shape-only edit.  This is the smallest theoretical structure that directly
removes the identified cause while preserving the physical water-air rising
bubble problem.
