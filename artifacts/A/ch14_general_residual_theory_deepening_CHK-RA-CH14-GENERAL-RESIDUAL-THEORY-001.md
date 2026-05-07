# CHK-RA-CH14-GENERAL-RESIDUAL-THEORY-001

Date: 2026-05-07

Scope: deepen the general residual-elimination theory.  The target is not a
static-droplet scheme.  The target is a structure-preserving capillary and
constraint force complex that eliminates scheme defects while preserving true
physical drive for oscillating droplets and arbitrary resolved perturbations.

## 1. Finite-Dimensional State

Let the interface state live in a finite-dimensional carrier space

```text
q in Q_h.
```

For the current implementation `q` is nodal `psi`, but the theory is written
for any carrier as long as the production endpoint is declared.  One physical
capillary/momentum step uses a labelled endpoint

```text
q_c = q_T
```

where `q_T` is the interface state after physical transport and before
reinitialization/profile projection.  Every force object in this theorem is
evaluated at `q_c`.

The physical model is encoded by a discrete action and constraints:

```text
E_h(q)      total conservative energy that may produce face force,
C_i,h(q)   holonomic constraints such as component volume, mass,
           wall/contact geometry, or imposed geometric invariants.
```

For pure capillarity,

```text
E_h(q) = sigma S_h(q).
```

For a more general system, conservative gravity or wall energy may be included
in `E_h`.  Nonconservative models do not belong in this capillary residual
elimination theorem unless they are given their own energy or dissipation law.

## 2. Endpoint and Velocity Complex

Let `U_f` be the face velocity space.  The implemented interface endpoint
differential is

```text
T_h(q_c): U_f -> T_{q_c}Q_h.
```

For the current conservative face-psi route,

```text
T_h(q_c)u_f = -D_f(P_f q_c * u_f).
```

The crucial point is that `T_h` is not a decorative modelling choice.  It is
the map whose adjoint defines force.  A force derived from another map is a
different theorem, even if it is visually close or geometrically appealing.

## 3. Pressure-Adjoint Momentum Pairing

The pressure/corrector complex is

```text
D_f: U_f -> pressure/source space,
G_A(q_c): pressure space -> U_f,
M_A(q_c): U_f metric.
```

`G_A` is the implemented pressure face action:

```text
G_A p = div_op.pressure_fluxes(p, rho(q_c), zero_jump_kwargs).
```

The metric `M_A` must be pressure-adjoint:

```text
<G_A p, w>_{M_A} = <p, D_f w>_{W_p}
```

for all admissible face velocities `w`, up to pressure gauge and boundary
conventions.  This is the theorem-level reason why arithmetic face mass and
affine-jump pressure weights cannot be swapped casually.  The Hodge quotient
is only physical in the metric that makes pressure do no work on divergence
free motions.

If this adjointness does not hold to tolerance, production must fail closed.
There is no safe fallback to a visually similar norm.

## 4. Variational Cochains

Define the Riesz representatives of energy and constraints by virtual work:

```text
<s, u>_{M_A}   = -dE_h(q_c)[T_h(q_c)u],
<B_i, u>_{M_A} =  dC_i,h(q_c)[T_h(q_c)u].
```

Equivalently,

```text
s   = -M_A^{-1} T_h(q_c)^* dE_h(q_c),
B_i =  M_A^{-1} T_h(q_c)^* dC_i,h(q_c).
```

This construction is shape-free.  It does not test whether an interface is a
circle, ellipse, Fourier mode, or any named geometry.  It tests the first
variation of the declared discrete energy under the declared production
endpoint.

## 5. Coupled Reaction Saddle

The physical drive is not `s` itself.  Pressure and constraint reactions are
allowed to remove components that do no work on admissible motions.  The
primitive system is

```text
h = s - G_A p - B mu,
D_f h = 0,
B^T M_A h = 0.
```

The admissible space is

```text
K = { u in U_f : D_f u = 0 and B^T M_A u = 0 }.
```

The force seen by momentum is the `M_A`-orthogonal projection of `s` onto `K`:

```text
h = Pi_K^{M_A} s.
```

Equivalently, pressure and constraints span the reaction space

```text
X = range(G_A) + span(B_i),
```

and

```text
h = s - Pi_X^{M_A}s.
```

This is the only valid "residual removal": remove reactions, not physical
drive.

## 6. Static and Dynamic Theorem

### Static Theorem

A state `q_c` is a discrete equilibrium if there exists `mu` such that

```text
dE_h(q_c)[T_h u] = sum_i mu_i dC_i,h(q_c)[T_h u]
```

for all divergence-free admissible face velocities `u`.  In the saddle form,
this is equivalent to

```text
h(q_c) = 0.
```

This is how static droplets, hydrostatic bubbles, contact-angle equilibria, or
other declared steady states must be certified.  A sampled continuum analytic
shape is only an initial guess unless it satisfies this finite-dimensional
equation.

### Dynamic Theorem

If the constrained first variation is nonzero, then

```text
h(q_c) != 0.
```

That is not a numerical defect.  It is the resolved physical drive.  For an
oscillating droplet, a non-elliptic perturbation, or any noncritical interface,
the scheme is correct only if this drive survives the pressure/constraint
saddle.

Thus the correct gate is two-sided:

```text
declared equilibrium      -> h ~= 0
declared non-equilibrium  -> h measurably nonzero and sign-correct
```

## 7. Energy Power Theorem

Assume pressure adjointness and the saddle constraints.  Then

```text
<s,h>_{M_A}
= <h + G_A p + B mu, h>_{M_A}
= ||h||_{M_A}^2.
```

Therefore

```text
dE_h(q_c)[T_h h] = -||h||_{M_A}^2 <= 0.
```

This is the mathematical separator between physical drive and defect.  The
drive `h` converts conservative energy into kinetic energy with the correct
sign.  A defect force has no such proof.

For finite-step time integration, replace `dE_h(q_c)` by a discrete gradient
`bar dE_h` satisfying

```text
E_h(q^{n+1}) - E_h(q^n) = bar dE_h [ q^{n+1} - q^n ].
```

Then the same saddle theorem applies to the finite-step cochain.  Without a
discrete-gradient identity, energy exchange can still be consistent to order,
but exact stepwise energy accounting is not proven.

## 8. Defect Decomposition

The observed acceleration can be decomposed conceptually as

```text
a_observed = h_physical + r_defect.
```

The defect has identifiable components:

```text
r_endpoint   force VJP uses T' but transport/corrector uses T_h,
r_metric     cochain uses M' but pressure-Hodge uses M_A,
r_constraint missing or wrongly signed B_i,
r_pressure   pressure_fluxes range differs from assumed G_A,
r_corrector  PPE RHS and corrector use different cochains,
r_auxiliary  reinit/remap/profile/grid rebuild changes energy but is counted
             as capillary work,
r_solver     algebraic solve residual above declared tolerance.
```

The general residual-elimination scheme targets only `r_defect`.  If a
candidate method reduces `h_physical`, it is not defect elimination; it is a
change to the physics.

## 9. CCD/FCCD/UCCD Closure

The capillary theorem is not complete until the force path closes through the
operator family that advances momentum.

### FCCD Closure

FCCD supplies the face endpoint and pressure complex:

```text
P_f q_c,
D_f,
G_A = pressure_fluxes(...),
projected face state.
```

The capillary cochain must be built on this same face complex.  A trace or
nodal force can be diagnostic only until its pullback to FCCD faces is proven
to satisfy the same virtual-work identity.

### UCCD Closure

UCCD convection must receive the projected face velocity containing the same
`h` from the pressure saddle:

```text
u_f^{n+1} = u_f^* + dt h + other projected effects.
```

No separate capillary advection velocity, no off-complex reconstruction, and
no post-corrector force rewrite are allowed.  Otherwise a residual can be
introduced after the theorem has already closed.

### CCD Closure

CCD viscosity sees the corrected velocity field reconstructed from the same
projected face state.  If viscosity uses a different velocity complex than the
one carrying capillary work, energy and momentum accounting split.  That split
must be either proven harmless by a consistency theorem or treated as a
defect.

The commutative path is therefore

```text
q_c
 -> FCCD endpoint T_h and pressure range G_A
 -> saddle drive h
 -> projected face velocity
 -> UCCD convection and CCD viscosity.
```

Any arrow mismatch is not an implementation detail.  It is a possible source
of the exact class of residual we are trying to eliminate.

## 10. Auxiliary Maps

Reinitialization, profile restoration, remap, and fitted-grid rebuild are not
capillary forces.  They are maps

```text
R_h: q_T -> q_R.
```

They may change `E_h`, `C_h`, phase volume, or the pressure metric.  The
allowed treatments are:

```text
1. prove endpoint equivalence: q_R and q_T induce the same theorem object;
2. ledger projection work separately from capillary work;
3. fail close for production interpretation.
```

They must not be hidden inside `h`.

## 11. Hypotheses Tightened

| ID | Hypothesis | Result |
|---|---|---|
| T01 | All Hodge residuals should be eliminated. | False; noncritical capillary modes are Hodge drive. |
| T02 | Only pressure and declared constraints may be eliminated. | True; follows from reaction work orthogonality. |
| T03 | Static residual and dynamic residual have the same cause. | Partly true only for theorem defects; dynamic physical drive is not a defect. |
| T04 | Static references require special static code. | False; they require the same finite-dimensional equilibrium equation as every declared steady state. |
| T05 | Oscillating droplets require a different capillary law. | False; they require the same law to preserve nonzero `h`. |
| T06 | CCD/FCCD/UCCD compatibility can be checked after physics. | False; it is part of the physics-to-momentum theorem. |
| T07 | Reinit residuals can be merged into capillary work. | False; they are auxiliary projection work unless endpoint-equivalent. |
| T08 | Metric mismatch is tolerable if visually small. | False for proof; it may be small numerically but invalidates the energy theorem. |
| T09 | Multiple components and contact constraints fit the same system. | True if each constraint supplies a `B_i` and rank/LICQ gates pass. |
| T10 | Nonconservative effects fit automatically. | False; they need a dissipation or forcing theorem outside this capillary saddle. |

## 12. Validation Gates

The general theory is falsifiable by the following gates:

```text
G1 endpoint VJP:
  dE_h[T_h u] + <s,u>_{M_A} ~= 0 for random and structured u.

G2 constraint VJP:
  dC_i[T_h u] - <B_i,u>_{M_A} ~= 0.

G3 pressure adjoint:
  <G_A p,w>_{M_A} - <p,D_f w>_{W_p} ~= 0.

G4 saddle:
  D_f h ~= 0 and B^T M_A h ~= 0 after solve.

G5 sign power:
  dE_h[T_h h] + ||h||_{M_A}^2 ~= 0.

G6 equilibrium:
  constructed or declared equilibria release from rest with h ~= 0.

G7 non-equilibrium:
  arbitrary resolved perturbations, including non-elliptic modes, have h != 0.

G8 corrector identity:
  PPE RHS and corrector use the same c_corrected = s - Bmu.

G9 CCD/FCCD/UCCD closure:
  the projected face velocity carrying h is the one consumed downstream.

G10 auxiliary ledger:
  reinit/remap/profile changes are recorded outside capillary work.
```

Failure of any of `G1` to `G5` is a theorem failure.  Failure of `G6` means the
declared equilibrium is not a finite-dimensional equilibrium.  Failure of `G7`
means the scheme is over-projecting and killing physics.

## 13. Implementation Consequence

The implementation should not be a "static ring cleaner."  It should be a
general variational residual framework:

```text
build theorem cochains -> solve reaction saddle -> pass h through FCCD face
state -> validate equilibrium/non-equilibrium gates -> ledger auxiliary maps.
```

Static droplets then become one validation case.  Oscillating droplets become
the paired nonzero-drive validation case.  Other systems add energies and
constraints but do not change the theorem skeleton.

## Verdict

The policy is viable and stronger than a static-specific fix.  The theory says
we can eliminate residuals that come from inconsistent endpoint, metric,
constraint, pressure, corrector, CCD/FCCD/UCCD, or auxiliary-map coupling.  It
also says we must not eliminate the constrained variational drive.  That is
exactly the separation needed for static droplets, oscillating droplets, and
future systems to share one capillary scheme.

[SOLID-X] Theory only.  No production behavior changed; no tested code
deleted; no FD/WENO/PPE fallback, damping/CFL workaround, smoothing, curvature
cap, benchmark branch, blanket projection, or QP-as-physics path introduced.
