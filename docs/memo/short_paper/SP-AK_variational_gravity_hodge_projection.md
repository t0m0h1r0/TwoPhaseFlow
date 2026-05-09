# SP-AK: Variational Gravity Hodge Projection for Rising Bubbles

**Status**: ACTIVE / theoretical replacement for nodal balanced-buoyancy
**Date**: 2026-05-09
**Scope**: water-air rising bubble, conservative common-flux state, gravity,
pressure projection, body-force Hodge decomposition
**Companion papers**: SP-AI, SP-AJ, SP-W, SP-X

## Abstract

The SI water-air rising-bubble failure cannot be repaired by changing the
pressure-history representation alone.  A restart from the saved `t=0.020 s`
state still enters the same blow-up band with both pressure-coordinate and
face-acceleration history.  Removing surface tension also fails, while removing
gravity lets the same state pass the old failure time.  Therefore the active
defect is the gravity/buoyancy force as it couples to the projection metric.

This paper reformulates gravity as a variational force covector, not as a
node-based body acceleration.  The force is the negative pullback of the
discrete gravitational potential through the same mass-transport differential
that updates the conservative state.  Pressure projection is then a weighted
Hodge decomposition in the transported face-mass metric.  Hydrostatic forces
are exactly pressure-range reactions; physical bubble rise is the remaining
divergence-free Hodge component.  Any implementation that computes
`(rho-rho_ref)g/rho` at nodes and interpolates it to faces has not implemented
this theorem unless it proves equality to the variational covector in the same
metric.

## 1. Verification Trigger

The pressure-coordinate history implementation passed its algebraic tests, but
it did not cure the rising-bubble blow-up.  The decisive short probes are:

```text
pressure_coordinate history:      fails near t ~= 0.02056
legacy face_acceleration history: fails near t ~= 0.02057
sigma = 0:                        fails
g = 0:                            passes the same time band
predictor assembly = none:        no meaningful improvement
projection_consistent_buoyancy:   no meaningful improvement
```

Thus the immediate theory target is not capillary history.  It is the
compatibility of gravity, mass transport, pressure range, and face velocity
projection.

## 2. Continuous Energy Reading

Use an upward coordinate `y` and a positive scalar `g`.  Gravity points in
the `-y` direction.  For incompressible phases with transported density

```text
rho_t + div(rho u) = 0,
div u = 0,
```

the mechanical energy is

```text
E = int 1/2 rho |u|^2 dx + sigma S(Gamma) + int rho g y dx.
```

Ignoring viscosity and boundary work,

```text
d/dt E = 0.
```

The gravitational force is therefore not primarily the acceleration
`-g e_y`.  It is the negative variation of

```text
Phi_g(rho) = int rho g y dx
```

under the same density transport that the velocity field induces.

For constant density this variation is a pure pressure gradient.  It must not
create velocity in a closed container.  For a two-phase bubble, the discontinuity
in transported mass leaves a non-pressure component; that component is the
physical buoyant drive.

This distinction is exactly a Hodge decomposition statement.

## 3. Discrete State

Let `C` be cells and `F` oriented faces.  Let

```text
V_c      diagonal cell-volume matrix
D        face-to-cell finite-volume divergence
q        liquid fraction
m(q)     cell mass = V_c (rho_g + (rho_l-rho_g) q)
u_f      face velocity
M_f(q)   transported face-mass metric
```

The conservative common-flux state is

```text
(q, m, p),  p_f = M_f(q) u_f.
```

The face inner product is

```text
<a,b>_M = a^T M_f(q) b.
```

Every force that can exchange energy with the flow must first be a face
covector `r_f`, i.e. an object that computes virtual power

```text
Power_r(w_f) = <r_f, w_f>
```

for any admissible virtual face velocity `w_f`.  A face acceleration is only
the Riesz representative

```text
a_f = M_f(q)^{-1} r_f.
```

Mixing a force covector from one metric with an acceleration in another metric
is a change of equation.

## 4. Transport Differential

The transport differential is part of the theorem.  For a virtual face velocity
`w_f`, the mass update induced by the production common-flux transport is

```text
T_m(q) w_f = -D( M_face_flux(q) w_f ).
```

Here `M_face_flux(q)` is the same face mass per unit face velocity used by the
common-flux ledger.  In the simplest sharp notation,

```text
M_face_flux(q) = rho_g P_f(1) + (rho_l-rho_g) P_f(q),
```

but the implementation must use the actual production face locus, limiter,
boundary closure, and nonuniform metric.  If the transport stage uses a
different map, that map is the one that defines `T_m`.

For phase variables one may also write

```text
T_q(q) w_f = -D( P_f(q) w_f ),
T_m(q) w_f = V_c (rho_l-rho_g) T_q(q) w_f + rho_g T_V w_f,
```

where `T_V w_f = -D(P_f(1) w_f)`.  The constant-density part is useful for
analysis because it is pressure-range under impermeable or periodic boundaries.
It must not be discretized by a different operator.

## 5. Gravity Covector

The discrete gravitational potential is

```text
Phi_g(m) = y^T (g m).
```

Its cell covector is

```text
ell_g = d Phi_g / d m = g y.
```

The gravitational face covector is defined by virtual work:

```text
<r_g, w_f> + <ell_g, T_m(q) w_f> = 0
for all w_f.
```

Therefore

```text
r_g(q) = -T_m(q)^T ell_g.
a_g(q) = M_f(q)^{-1} r_g(q).
```

This is the production definition.  The formula is deliberately parallel to the
capillary variational force

```text
r_sigma(q) = -T_q(q)^T d(sigma S_h)/dq.
```

The body-force expression `-(rho-rho_ref)g e_y` is only a coordinate
representative.  It is valid in production only when the following identity has
been proven in the active discrete metric:

```text
< M_f a_body, w_f > = -< ell_g, T_m(q) w_f >
for all tested w_f.
```

Without this identity, nodal balanced-buoyancy is a heuristic.

## 6. Pressure Range and Hodge Split

Let the pressure correction be a constraint reaction in the same metric.
For a scalar pressure coordinate `pi`, define the pressure acceleration range

```text
R_p = { M_f(q)^{-1} G_f pi : pi in Q_h / constants }.
```

Equivalently, if `G_f = D_f^T W_c` up to sign convention, the pressure force
covectors are `range(G_f)`.

Let boundary constraints be `C_b u_f = b_b`.  The admissible velocity space is

```text
K(q) = { w_f : D_f w_f = 0, C_b w_f = 0 }.
```

The force Hodge decomposition is:

```text
a_g = Pi_R^M a_g + H_R^M a_g,
Pi_R^M a_g in R_p,
H_R^M a_g in K(q).
```

Here orthogonality is in `<.,.>_M`.  In covector form,

```text
r_g = G_f pi_g + M_f h_g,
D_f h_g = 0,
C_b h_g = 0,
<h_g, M_f^{-1}G_f pi>_M = 0.
```

`G_f pi_g` is hydrostatic pressure reaction.  `h_g` is the physical buoyancy
drive.  A method that applies the full nodal body acceleration before projection
and then adds the same force again in the corrector must be algebraically
equivalent to this split.  Otherwise it can inject work into high-frequency
interface modes.

## 7. Static and Dynamic Conditions

### 7.1 Single-Phase Hydrostatic Column

If `rho` is constant and boundaries are impermeable or periodic, then

```text
r_g = G_f pi_h
```

for `pi_h = rho g y` up to gauge.  Therefore

```text
H_R^M a_g = 0.
```

This is the first well-balanced gate.  It must hold on uniform and nonuniform
grids.

### 7.2 Flat Two-Phase Hydrostatic Interface

For a horizontal interface at rest, gravity and Young-Laplace reactions must
lie in the augmented pressure/jump/component range:

```text
r_g + r_sigma = G_f pi + B_jump j + B_comp lambda.
```

The Hodge residual must vanish:

```text
H_aug^M (a_g + a_sigma) = 0.
```

This gate is stronger than checking only `D_f(a_g+a_sigma)`.  A divergence-free
residual can still drive parasitic flow.

### 7.3 Rising Bubble

A circular gas bubble in water under gravity is not a static critical point.
The gravitational Hodge component should be nonzero:

```text
||H_aug^M a_g||_M > 0.
```

But its work scale is bounded by the physical potential drop:

```text
Power_g(u) = <r_g,u> = -d Phi_g(q)[T_m(q)u],
|Power_g| = O(Delta rho g R U).
```

It must not produce pressure or kinetic scales many orders above

```text
Delta p_h = Delta rho g L_y,
U_b = sqrt(g D),
U_sigma = sqrt(sigma/(rho_l R)).
```

The high-k fraction is a witness of unaccounted work, not a filter target.

## 8. Projection Step With External Covectors

Let all explicit conservative forces produce a covector

```text
r_ext = r_g + r_sigma + r_mu + r_other.
```

The force-predicted velocity is the mass-metric impulse

```text
u^dagger = u^n + dt M_f^{-1} r_ext.
```

The pressure projection is

```text
u^{n+1} = argmin_u 1/2 ||u-u^dagger||_M^2
subject to D_f u = 0 and C_b u = b_b.
```

The KKT system is

```text
M_f(u^{n+1}-u^dagger) + G_f pi + C_b^T lambda = 0,
D_f u^{n+1} = 0,
C_b u^{n+1} = b_b.
```

This is equivalent to projecting the total external acceleration and retaining
only its admissible Hodge component.  Pressure does no work:

```text
1/2 ||u^{n+1}||_M^2 <= 1/2 ||u^dagger||_M^2
```

up to boundary work and solver tolerance.

## 9. Energy Ledger

For a force substep with fixed `q,m,M_f`, the certified work is

```text
Delta K_force = K(M_f,u^dagger) - K(M_f,u^n),
W_g           = dt <r_g, u_theta>,
W_sigma       = dt <r_sigma, u_theta>,
```

with a declared time quadrature `u_theta`.  The required gravity identity is

```text
W_g + Delta Phi_g = eps_g.
```

For an explicit first-order force stage,

```text
Delta Phi_g ~= d Phi_g[T_m(q)(dt u_theta)].
```

For a higher-order common-flux stage, `Delta Phi_g` must be computed from the
same stage ledger that updated `m`.  If the step cannot name `eps_g`, the
gravity route is not certified.

The projection ledger is

```text
Delta K_projection =
  K(M_f,u^{n+1}) - K(M_f,u^dagger) <= eps_Pi.
```

`eps_Pi` must be non-positive up to linear-solver tolerance.  A positive
projection energy jump means pressure and velocity are not using the same
metric.

## 10. Why the Old Split Is Insufficient

The common continuum split

```text
rho' g = -grad(rho' g y) + g y grad rho'
```

is an identity only before discretization.  In the current failure mode the
problem is precisely discrete: nonuniform grid weights, phase-separated face
coefficients, face-native projection, conservative transport, and pressure
history do not all see the same space.

The old implementation pattern can fail in three ways:

```text
1. nodal acceleration is divided by rho before the face mass metric is chosen;
2. hydrostatic scalar pressure is differentiated by a pressure operator that is
   not the transpose of the mass transport differential;
3. the corrector adds force faces and pressure faces that are not covectors in
   the same M_f space.
```

Any of these breaks the theorem even if the code is called
`balanced_buoyancy`.

## 11. CCD/FCCD/UCCD Compatibility

The formulation is orthogonal to the stencil family:

```text
FCCD supplies the conservative face incidence and transport differential T_m.
CCD supplies elliptic/stress solves only when their work pairing is explicit.
UCCD may evaluate conservative momentum fluxes, not hidden velocity damping.
DCCD may be a diagnostic or certified projection, never a silent stabilizer.
```

The compatibility condition is not the operator name.  It is the identity

```text
<r_g,w_f> = -<ell_g,T_m w_f>
```

and the pressure projection inequality in the same `M_f`.

## 12. Verification Gates

The route is implementation-ready only after these tests pass.

### G1. Transport-adjoint gravity test

For random `w_f`,

```text
<r_g,w_f> + <ell_g,T_m w_f> = 0
```

on uniform, nonuniform, wall, periodic, and mixed boundary grids.

### G2. Single-phase hydrostatic null Hodge

For constant `q`,

```text
||H_R^M a_g||_M <= tau_hydro
```

and projection from rest remains at rest.

### G3. Flat-interface hydrostatic plus jump null Hodge

For a horizontal two-phase column,

```text
||H_aug^M(a_g+a_sigma)||_M <= tau_flat.
```

This includes the jump/affine pressure range and wall constraints.

### G4. Rising-bubble finite Hodge scale

For the initial bubble,

```text
0 < ||H_aug^M a_g||_M < C sqrt(gD)
```

after dimensional normalization.  The Hodge component should be nonzero but not
near-Nyquist dominated.

### G5. Energy identity

For one force step,

```text
W_g + Delta Phi_g = eps_g,
|eps_g| <= tau_g.
```

### G6. Projection non-increase

```text
Delta K_projection <= tau_Pi.
```

### G7. Restart invariance

Saving and restoring all `q,m,p,M_f,pressure-coordinate` state before a step
must reproduce the same `r_g`, pressure reaction, and `u^{n+1}`.

### G8. GPU/CPU identity

The vectorized `T_m`, `T_m^T`, `M_f`, and Hodge diagnostics must use `backend.xp`
and agree CPU/GPU within the existing roundoff envelopes.  No host loop is part
of the production force path.

## 13. Implementation Consequence

The next implementation should not add another option to the old
body-acceleration route.  It should introduce a force-covector layer:

```text
GravityPotentialCovector:
  input: q, common-flux face mass, grid y, g
  output: r_g faces, a_g = M_f^{-1} r_g
  certificate: adjoint residual, energy residual
```

The PPE and corrector should consume `a_g` only through the same pressure
projection KKT route that consumes capillary and pressure-history cochains.

YAML should expose the contract, not a tuning knob:

```yaml
numerics:
  momentum:
    terms:
      gravity:
        formulation: variational_potential
        transport_adjoint: common_flux
        metric: transported_face_mass
        hodge_gate: fail_close
```

The legacy names `balanced_buoyancy` and `projection_consistent_buoyancy` can
remain as compatibility aliases only after they route to this covector theorem.

## 14. Negative Knowledge

Reject the following as primary remedies:

```text
CFL reduction
velocity damping
DCCD/UCCD high-k filtering
curvature cap
pressure smoothing
node-to-face body-force interpolation
benchmark-specific bubble branch
hydrostatic split with a different gradient than PPE/corrector
gravity=0 or sigma=0 as a production workaround
```

They may change when the blow-up appears, but they do not prove a discrete
energy law.

## 15. Decision

The corrected theory is:

```text
All conservative forces are energy-gradient covectors pulled back by the
production transport differential.  Pressure projection is the M_f-Hodge
reaction that removes the constrained range component.  The remaining Hodge
component is the physical non-pressure drive.
```

For rising bubbles this means:

```text
gravity = -T_m^T d Phi_g,
capillary = -T_q^T d(sigma S_h),
pressure = constraint reaction in the same M_f,
motion = Hodge remainder after the same KKT projection.
```

This is the formulation to implement.  The old nodal body-force split is only
a derived representative after it passes the transport-adjoint and energy
gates above.
