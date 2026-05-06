# SP-AD: Variational Coupling of Ridge-Eikonal Projection and Interface Transport

**Status**: Research memo / formulation draft
**Date**: 2026-05-06
**Related**: [SP-B](SP-B_ridge_eikonal_hybrid.md), [SP-E](SP-E_ridge_eikonal_nonuniform_grid.md), [SP-AA](SP-AA_capillary_energy_variational_geometry.md), [SP-AC](SP-AC_ale_discrete_gradient_capillary_work.md), [WIKI-X-019](../../wiki/cross-domain/WIKI-X-019.md), [WIKI-T-155](../../wiki/theory/WIKI-T-155.md), [WIKI-T-156](../../wiki/theory/WIKI-T-156.md)

---

## Abstract

This memo records a formulation path for coupling Ridge-Eikonal reconstruction
with the physical interface-transport equation without turning reinitialization
into an unaccounted energy source.  The main conclusion is positive but
conditional: a coupled formulation is viable only if the physical interface
motion, metric reconstruction, and capillary pressure work share a single
discrete variational contract.  Simply adding a Ridge-Eikonal or Eikonal
pseudo-time right-hand side to the interface transport equation is rejected,
because it creates a non-material interface velocity whose surface-energy work
is not paired with the projection/corrector.

The preferred direction is a constrained transport/projection step:

1. transport the interface by the projection-native face flux;
2. reconstruct the metric/profile by a Ridge-Eikonal projection that is
   identity on static equilibria and preserves the interface trace in
   fixed-topology periods;
3. route the capillary work through the same face divergence adjoint used by
   the transport update;
4. measure and gate any residual surface-energy change caused by projection.

---

## 1. Non-negotiable constraints

### C1. Topology and metric remain separate

The project already separates the topology field and the metric field:

- `xi_ridge` carries topology and deliberately violates the Eikonal condition.
- `phi` carries metric consistency and is reconstructed as a signed-distance
  field after a ridge set is admissible.
- `psi = H_eps(-phi)` is the conservative level-set field consumed by the
  finite-volume-like transport and material interpolation.

A single scalar field cannot simultaneously be a material conservative
interface field, an exact SDF everywhere, and a topology-changing field.  Any
"coupled" scheme must therefore couple roles, not collapse them.

### C2. Physical interface motion is owned by the face flux

The physical fixed-topology interface transport must use the canonical projected
face velocity:

```text
psi* = psi^n - dt D_f( (P_f psi^theta) u_f )
```

Here `D_f` is the same face divergence that appears in the projection closure,
and `u_f` is the divergence-free canonical face state.  Reconstructing nodal
velocity and building a second face flux is a different discrete conservation
law and is not admissible for this coupling.

### C3. Reinitialization is metric/gauge projection, not physical motion

Ridge-Eikonal, FMM, xi-SDF, and logit/profile restoration change the metric
representation.  Away from topology events, those changes must not be treated
as a material normal velocity.  If a projection changes the zero level set or
the trace surface energy in a static droplet, it has introduced a numerical
forcing term.

### C4. Surface-energy work uses the transport adjoint

The capillary face cochain must be the adjoint of the same transport map that
moves the interface.  In symbolic form, if

```text
delta psi = -dt D_f( (P_f psi) delta u_f ),
```

then a surface-energy covector `g_bar` gives

```text
delta S_h = <g_bar, delta psi>
          = -dt < (P_f psi) (-D_f)^T g_bar, delta u_f >_f.
```

Thus the capillary face cochain must live in the same face space as the
projection corrector.

### C5. Static projection identity is a theorem target

For a static circular droplet with Young-Laplace pressure jump, if

```text
u_f = 0,
psi = H_eps(-phi),
|grad phi| = 1,
```

then the metric projection must satisfy

```text
Pi_h(psi) = psi,
S_h(Pi_h(psi)) = S_h(psi),
Gamma(Pi_h(psi)) = Gamma(psi).
```

This is a stronger condition than mass conservation.  A volume-preserving
uniform `delta phi` shift can still move `Gamma` and change `S_h`.

---

## 2. Continuous formulation

### 2.1 Fixed topology

The physical interface is the geometric set `Gamma(t)`.  Its normal velocity is
the fluid normal velocity:

```text
V_Gamma = u . n.
```

The signed-distance field is not materially transported everywhere.  Instead,
after `Gamma(t)` is known, `phi(t)` is the viscosity solution of

```text
|grad phi| = 1,       phi = 0 on Gamma(t),
```

and `psi = H_eps(-phi)`.

This distinction matters.  The equation

```text
phi_t + u . grad phi = 0
```

is a valid level-set interface equation only at the zero level set.  Requiring
it to hold while also enforcing `|grad phi| = 1` everywhere overdetermines the
off-interface gauge.

### 2.2 Topology-changing periods

During topology changes, `xi_ridge` can evolve in physical time:

```text
partial_t xi_ridge + u . grad xi_ridge = eps_diff Delta xi_ridge.
```

The ridge set defines `Gamma`, then `phi` is reconstructed from `Gamma`.
The diffusion term is numerical regularization, not physical capillary work.  A
production scheme must therefore record its contribution as topology/metric
dissipation or reject a step that creates positive unaccounted surface energy.

### 2.3 Energy law

The target discrete law is the capillary/viscous analogue of

```text
d/dt (K_h + sigma S_h) + D_visc + D_metric >= 0 only as dissipation,
```

or, equivalently,

```text
K_h^{n+1} - K_h^n
+ sigma (S_h^{n+1} - S_h^n)
+ D_visc
+ D_metric
<= 0.
```

`D_metric` is zero for fixed-topology identity projection and non-negative for
accepted regularizing projections.  It must not appear as kinetic energy.

---

## 3. Discrete constrained transport/projection step

Let `q` denote the nodal conservative level-set field `psi`.  Let `M_h` be the
cell-volume mass matrix, `D_f` the projection-native face divergence, and `P_f`
the FCCD face-value operator.

### 3.1 Physical transport

Compute the material interface update:

```text
q* - q^n + dt D_f( (P_f q^theta) u_f ) = 0.
```

The volume identity is inherited from the face divergence:

```text
1^T M_h (q* - q^n) = 0
```

up to boundedness clamps and roundoff.  Any clamp must be recorded as a separate
non-transport correction.

### 3.2 Metric projection

The Ridge-Eikonal/profile projection is a constrained closest-point map:

```text
(q^{n+1}, phi^{n+1}) = Pi_h(q*)
```

defined by

```text
minimize    1/2 ||q - q*||_W^2
subject to  q = H_{eps(x)}(-phi),
            E_h(phi) = 0                         in the interface band,
            1^T M_h (q - q^n) = 0,
            Gamma(q) = Gamma(q*)                 fixed topology,
            S_h(Gamma(q)) = S_h(Gamma(q*))       fixed topology.
```

`E_h(phi)=0` denotes the discrete Eikonal constraint.  For a topology event,
the last two fixed-topology constraints are replaced by an admissible ridge-set
transition and an explicit metric/topology dissipation budget.

This projection is the mathematical version of "Ridge-Eikonal plus interface
transport solved together."  It is not a source term added to the transport
equation; it is a constraint manifold attached to the end of the physical
transport step.

### 3.3 KKT form

The same projection can be written as a KKT system:

```text
W(q - q*) + C_H(q,phi)^T lambda_H
          + C_E(phi)^T lambda_E
          + M_h 1 lambda_M
          + C_Gamma(q)^T lambda_Gamma
          + C_S(q)^T lambda_S = 0,

C_H(q,phi) = q - H_{eps(x)}(-phi) = 0,
C_E(phi)  = E_h(phi) = 0,
1^T M_h(q-q^n) = 0,
C_Gamma(q,q*) = 0,
C_S(q,q*) = 0.
```

The Lagrange multipliers live inside the metric projection.  They do not become
unlabelled forces in the momentum equation.

---

## 4. Discrete capillary work after projection

The key split is

```text
delta q_T  = q*       - q^n        physical transport
delta q_Pi = q^{n+1}  - q*         metric projection
```

Only `delta q_T` is generated by the fluid face velocity.  Therefore only
`delta q_T` may be paired with the velocity work identity.

### 4.1 Transport discrete gradient

Construct `g_bar_T` so that

```text
<g_bar_T, delta q_T> = S_h(Gamma(q*)) - S_h(Gamma(q^n)).
```

In fixed-topology periods the projection must preserve `Gamma`, so

```text
S_h(Gamma(q^{n+1})) = S_h(Gamma(q*)).
```

The capillary face cochain is then

```text
c_sigma,f = -sigma (P_f q^theta) ((-D_f)^T g_bar_T).
```

This is the same algebraic shape as the existing transport-adjoint capillary
map, but the endpoint pair is the physical transport pair, not an unlabelled
transport-plus-reinitialization pair.

### 4.2 Projection-energy audit

The projection must report

```text
Delta S_Pi = S_h(Gamma(q^{n+1})) - S_h(Gamma(q*)).
```

Acceptance rules:

```text
fixed topology:       |Delta S_Pi| <= tol_S and |delta Gamma_Pi| <= tol_Gamma
regularizing topology: Delta S_Pi <= tol_positive, with D_metric recorded
static equilibrium:    q^{n+1} == q* == q^n within tolerance
```

Positive `Delta S_Pi` in a static or fixed-topology run is a hard failure, not a
CFL issue.

---

## 5. Pressure-jump range closure

Even if the capillary cochain is variational, static droplets still require a
range condition: the capillary face cochain must be representable by the
pressure-gradient/corrector space.

Let `A_f G_f` be the same face coefficient and gradient used by the projection
corrector.  Define the range projection

```text
p_sigma = argmin_p || A_f G_f p - c_sigma ||_{A_f^{-1}}^2,
h_sigma = c_sigma - A_f G_f p_sigma.
```

The static-droplet gate is

```text
||h_sigma||_face / max(||c_sigma||_face, eps) <= tol_hodge.
```

The previous static-droplet RCA found precisely the dangerous case: a cochain
can have tiny divergence but nonzero solenoidal/Hodge content.  A divergence
gate alone is therefore insufficient; the face cochain itself must be range
compatible.

---

## 6. Trace-primary alternative

The cleaner long-term formulation is to make the interface trace the surface
energy variable:

```text
a = trace DOFs of Gamma,
S_h = S_h(a).
```

For an edge crossing between nodal values `q_i` and `q_j`,

```text
theta = (1/2 - q_i) / (q_j - q_i),
x_cross = x_i + theta (x_j - x_i).
```

The Jacobian `J = partial a / partial q` maps a trace-space surface-energy
gradient to a nodal covector:

```text
g_q = J^T grad_a S_h.
```

This separates physical interface geometry from the diffuse profile.  A
Ridge-Eikonal projection that changes only the off-interface profile then has
no surface-energy effect, because `S_h` depends on `Gamma`, not on the gauge
values away from the trace.

This route is mathematically preferable for static droplets, but it requires a
robust trace Jacobian, topology-event trace bookkeeping, and the same face-space
range closure above.

---

## 7. Rejected formulations

### R1. Add reinitialization RHS to interface transport

Rejected:

```text
q_t + div(q u) = R_reinit(q).
```

`R_reinit` is not a physical flux driven by `u_f`.  Unless it is written as a
constrained metric projection with an energy budget, it creates or removes
surface energy without a valid pressure-work pairing.

### R2. Enforce material transport and exact SDF everywhere

Rejected:

```text
phi_t + u . grad phi = 0,
|grad phi| = 1 everywhere at all times.
```

The first equation is an interface equation at `phi=0`; away from the interface
it fixes a gauge.  The second equation fixes a different gauge.  Requiring both
globally overdetermines the field except in special rigid motions.

### R3. Volume-only reinitialization acceptance

Rejected.  Volume conservation does not imply zero level-set preservation,
surface-energy preservation, or pressure-work closure.

### R4. Curvature smoothing, damping, CFL reduction, or artificial broadening

Rejected as root fixes.  They may reduce symptoms but do not close the
variational identity.

---

## 8. Implementation research ladder

### P0. Diagnostics, no algorithm change

Add per-step diagnostics:

```text
reinit_zero_level_displacement
reinit_surface_energy_delta
reinit_volume_delta
static_projection_identity_error
capillary_work_closure_residual
capillary_hodge_residual
```

These are required before changing the algorithm, because they identify whether
energy enters through projection, through the face cochain range defect, or
through both.

### P1. Fixed-topology identity projector test

Build an isolated projector test on an analytic circle:

```text
q = H_eps(-phi_circle)
Pi_h(q) == q
Gamma(Pi_h(q)) == Gamma(q)
S_h(Pi_h(q)) == S_h(q)
```

Run this on uniform and interface-fitted grids.

### P2. Split transport/projection energy accounting

Change the capillary discrete-gradient endpoint accounting from
`q^n -> q^{n+1}` to the labelled pair:

```text
transport:  q^n -> q*
projection: q*  -> q^{n+1}
```

Fail if fixed-topology projection changes trace energy.

### P3. Face-space range projection

Implement the Hodge/range residual gate for `c_sigma`.  Static droplets should
not accept a capillary cochain that is divergence-small but solenoidal-large.

### P4. Ridge-primary topology event path

Only after P0--P3 are stable, evolve `xi_ridge` in physical time, extract
`Gamma`, reconstruct `phi`, and charge the ridge diffusion/topology transition
to `D_metric`.

---

## 9. Verdict

The coupled theory is viable, but the coupling is variational, not additive.
Ridge-Eikonal reconstruction can be made compatible with interface transport if
it is treated as an admissibility/metric constraint on the transported
interface, and if the surface-energy and pressure-work pairings are written in
the same face-space algebra as the projection.

The immediate research target is therefore not "solve one larger advection
equation"; it is:

```text
projection-native interface transport
+ identity-preserving Ridge-Eikonal metric projection
+ transport-adjoint capillary discrete gradient
+ pressure-gradient range closure
```

This is a root-level formulation path and does not rely on damping, CFL tuning,
curvature caps, smoothing, or unlabelled alternate calculation schemes.
