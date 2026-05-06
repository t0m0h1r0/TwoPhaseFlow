# CHK-RA-CH14-CAP-VARIATIONAL-THEORY-001 - Shape-Agnostic Closed-Interface Capillary Theory

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`

## Purpose

This note closes the theory target for the ch14 pressure-jump capillary
problem without using shape recognition, benchmark names, or implementation
convenience as correctness criteria.

The selected principle is:

```text
capillarity must be the face-space pullback of a discrete constrained
surface-energy variation, in the same pressure/corrector complex that applies
the velocity projection.
```

Circles, ellipses, squares, random modes, and multi-component states are only
probes of this principle.  No production law may ask which one is present.

## 1. Discrete Objects

Use the following finite-dimensional spaces.

```text
Q_h      interface configuration space
F_h      canonical face-velocity space
C_h      cell/divergence space
P_h      pressure space
M_f      physical face inner-product matrix
D_f      face divergence, F_h -> C_h
G_f      pressure gradient, P_h -> face gradients
A_f      face inverse-density/coefficient operator
R_h      pressure acceleration range = range(A_f G_f)
```

The production pressure projection uses:

```text
L_h p = D_f A_f G_f p,
a_f   = A_f G_f p - s_f,
```

where `s_f` is the capillary face cochain supplied to the projection.  The
Hodge residual is:

```text
Pi_R s_f = A_f G_f L_h^{-1} D_f s_f,
H_R s_f  = s_f - Pi_R s_f.
```

With the existing diagnostic convention,

```text
||x||_M^2 = sum_f measure_f x_f^2 / A_f.
```

The exact measure factors are those used by the same `D_f,A_f,G_f` production
complex, not a separately chosen surface quadrature.

## 2. Surface Energy And Transport

Let `q in Q_h` denote the actual closed-interface degrees of freedom used for
surface geometry.  It may be represented by trace points, a polygon, or a
carrier field plus a trace extractor, but the energy depends only on the
trace:

```text
S_h(q)      discrete interface length/area
V_m,h(q)   discrete volume of connected component m
E_h(q)     sigma S_h(q)
```

The physical transport map is the differential of the interface update with
respect to face velocity:

```text
T_h(q): F_h -> T_q Q_h.
```

For the current CLS/FCCD carrier this is represented, before reinit, by the
adjoint-compatible transport:

```text
delta psi_T[w_f] = -dt D_f(P_f psi^theta w_f).
```

For a polygonal interface it is the induced motion of cut points or vertices
under the same face velocity.  The exact representation is negotiable; the
contract is not.  The capillary covector must use the adjoint of the same
transport map that the momentum step uses.

## 3. Two Equivalent Forms Of The Correct Law

There are two mathematically equivalent ways to state the correct force.  They
must not be confused.

### 3.1 Projection Form: Surface Covector Plus Pressure Reaction

First build the unconstrained surface-energy cochain:

```text
s_f = - T_h(q)^* d_q [sigma S_h(q)].
```

The sign convention is chosen so that positive face work by `s_f` decreases
surface energy.  For every virtual face velocity `w_f`:

```text
<s_f, w_f>_M = - d_q[sigma S_h][T_h w_f].
```

Volume constraints produce component reaction covectors:

```text
b_m,f = T_h(q)^* d_q V_m,h(q).
```

At a constrained equilibrium there must exist multipliers `lambda_m` such
that:

```text
s_f + sum_m lambda_m b_m,f
```

has no action on admissible incompressible face velocities.  In pressure
language, the `b_m` reactions are the component pressure-jump modes.  Therefore
they must live in the pressure acceleration range, or the pressure range must
be augmented:

```text
R_aug = range(A_f G_f) + span{b_m}.
```

The production acceleration is:

```text
a_f = Pi_{R_aug} s_f - s_f = -H_{R_aug} s_f.
```

This form preserves pressure contrast natively: `lambda_m` is pressure data,
not a lost diagnostic.

### 3.2 Eliminated Form: Constrained Energy Residual

If and only if the component reactions `b_m` are represented in the same
pressure complex, one may eliminate them from the driving covector:

```text
c_f(lambda) =
  - T_h(q)^* d_q [sigma S_h(q) - sum_m lambda_m V_m,h(q)].
```

This is the residual capillary cochain after exact pressure reaction has been
removed.  It is the meaning of the previously written formula:

```text
c_sigma = T_h^* d_q [sigma S_h - sum_m lambda_m V_m,h].
```

That formula is not a license to discard pressure jumps.  It is valid only
when the eliminated `lambda_m V_m,h` terms are represented by the pressure
unknowns used by PPE, corrector, HFE history, and diagnostics.

## 4. The Main Theorem

### Theorem 1 - Hodge Residual Equals Constrained Capillary Drive

Assume:

1. `s_f = -T_h^* d(sigma S_h)` is the exact transport-adjoint surface-energy
   covector.
2. `R_aug` is the same pressure acceleration range used by the PPE and
   corrector, including any required component constraint reactions.
3. The Hodge projection is the `M_f`-orthogonal projection onto `R_aug`.
4. Boundary conditions and admissible face velocities match production.

Then:

```text
H_{R_aug} s_f = 0
```

if and only if the discrete interface is a constrained critical point of
`sigma S_h` under the component volume constraints, as seen by the transport
map `T_h`.

Moreover, for any noncritical resolved interface mode, there exists an
admissible incompressible face velocity `w_f` such that:

```text
<H_{R_aug} s_f, w_f>_M != 0.
```

Thus the same object gives both stillness of true equilibria and release of
all noncritical modes.

### Proof Sketch

Let `K_h` be the `M_f`-orthogonal complement of `R_aug`.  For the production
projection this is the divergence-free, boundary-compatible Hodge subspace
modulo the chosen pressure gauge:

```text
K_h = { w_f in F_h : <r_f,w_f>_M = 0 for all r_f in R_aug }.
```

By definition of orthogonal projection:

```text
<H_{R_aug} s_f, w_f>_M = <s_f, w_f>_M
```

for every `w_f in K_h`.  By the virtual-work definition:

```text
<s_f,w_f>_M = -d(sigma S_h)[T_h w_f].
```

Pressure and component multipliers span exactly the constraint reactions in
`R_aug`, so testing only against `K_h` is equivalent to testing surface-energy
variation only on admissible volume-preserving motions.  Therefore
`H_{R_aug} s_f` vanishes exactly when the constrained first variation vanishes
on all admissible motions.  If the first variation is nonzero for any
admissible motion, its Riesz representative in `K_h` is nonzero, hence
`H_{R_aug} s_f != 0`.

No step in the argument refers to curvature being constant, the shape being a
circle, or a perturbation being elliptical.

## 5. Necessary Conditions

Any production remedy must satisfy all of these conditions.

### N1. Transport-Adjoint Energy Identity

For arbitrary sampled face velocities:

```text
<s_f,w_f>_M + d(sigma S_h)[T_h w_f] = 0.
```

Finite-difference falsification:

```text
err(eps,w_f) =
| <s_f,w_f>_M
  + (sigma S_h(q + eps T_h w_f) - sigma S_h(q - eps T_h w_f))/(2 eps) |
```

must converge to the finite-difference floor as `eps` enters the linear
regime.

### N2. Component Constraint Representation

For every connected component:

```text
b_m = T_h^* dV_m,h
```

must be exactly represented by the pressure/jump complex:

```text
b_m in R_aug.
```

If `b_m notin range(A_f G_f)`, the pressure space is incomplete for closed
interfaces and must be augmented.  A scalar curvature mean cannot repair this
by itself.

### N3. Same Operator Everywhere

The same `R_aug` must be used by:

```text
PPE RHS,
pressure solve,
velocity corrector,
pressure history,
HFE representative,
range/Hodge diagnostics.
```

A pressure enrichment used only for diagnostics is not a theorem.  A jump
cochain used only in the corrector but not in the PPE is also not a theorem.

### N4. Shape-Agnostic Mode Completeness

The cochain must act on the whole resolved image of `T_h`, not on a named
modal basis:

```text
T_h(F_h) includes low modes, high modes, asymmetric modes,
component interactions, and locally rough but resolved modes.
```

If the algorithm deletes all nonconstant Hodge content, it fails.  If it keeps
unverified Hodge content that is not an energy gradient, it also fails.

### N5. Reinit Split

The physical step is:

```text
q^n -- T_h(u_f) --> q_T
q_T -- Pi_h    --> q^{n+1}.
```

Capillary work pairs only with `q^n -> q_T`.  Any change in surface energy or
volume during `Pi_h` is:

```text
Delta S_Pi, Delta V_Pi
```

and must be reported as representation projection, metric dissipation, or
topology defect.  It must not be counted as reversible surface-tension work.

## 6. Sufficient Construction

A construction is sufficient if it does the following.

### Step S1. Choose The Trace Geometry

Define `q` as the closed-interface trace DOF.  The safest candidate is a
polygonal or cut-cell trace whose vertices/cut points are exactly those used
to compute:

```text
S_h(q), V_m,h(q), component labels.
```

Diffuse carrier values away from the trace may support transport and
conditioning, but they are not independent surface-energy DOFs.

### Step S2. Define The Transport Differential

Derive `T_h(q) w_f` from the actual face transport used before reinit.  For a
level-set trace this means differentiating the cut-point motion implied by
the transported carrier.  For a polygon this means moving trace points by the
interpolated normal component of `w_f`.

### Step S3. Differentiate The Energy

Compute:

```text
dS_h(q), dV_m,h(q)
```

with respect to the same trace DOFs.  Do not replace this with a curvature
estimator unless the estimator is proven to be the derivative of `S_h`.

### Step S4. Pull Back To Faces

Build:

```text
s_f = -T_h^* d(sigma S_h),
b_m =  T_h^* dV_m,h.
```

This is the only point where capillarity enters the face space.

### Step S5. Close The Pressure Complex

If all `b_m` already lie in `range(A_f G_f)`, the existing pressure complex is
sufficient.  If not, augment it:

```text
A_f G_f p  ->  A_f G_f p + B lambda,
B lambda   = sum_m lambda_m b_m.
```

The PPE operator becomes:

```text
D_f [A_f G_f p + B lambda] = rhs + D_f s_f.
```

The corrector uses the same full cochain:

```text
a_f = A_f G_f p + B lambda - s_f.
```

### Step S6. Project Only Through The Corrector

The projection `Pi_R` is allowed as the mathematical pressure solve and as a
diagnostic.  It is not allowed as a replacement:

```text
invalid: s_f <- Pi_R s_f
valid:   a_f = Pi_R s_f - s_f
```

The first line deletes all Hodge drive.  The second line is the incompressible
capillary acceleration.

## 7. Finite-Step Theorem

For a finite transport increment `Delta q = q_T - q^n`, an infinitesimal
gradient is not enough to close the energy ledger.  The finite-step cochain
must satisfy a discrete-gradient identity:

```text
<s_bar_f, Delta x_f>_M
  = -sigma [S_h(q_T) - S_h(q^n)]
```

and, with constraints,

```text
<s_bar_f + sum_m lambda_bar_m b_bar_m, Delta x_f>_M
  = -[sigma Delta S_h - sum_m lambda_bar_m Delta V_m,h].
```

A Gonzalez-type construction is admissible only if:

1. the correction is applied in the same face metric `M_f`;
2. the direction used by the correction is the actual transport increment;
3. zero-step and pure-gauge steps are safe;
4. the component-volume terms use the same `V_m,h` as the pressure reactions.

Then the fixed-topology energy ledger can target:

```text
K^{n+1} - K^n
+ sigma [S_h(q_T) - S_h(q^n)]
+ D_visc
+ D_metric
= R_num,
```

with `D_metric=0` for trace-preserving reinit.

## 8. Why The Known Non-Fixes Fail

### Blanket Range Projection

`s_f <- Pi_R s_f` makes:

```text
a_f = Pi_R s_f - Pi_R s_f = 0
```

for a zero-predictor release.  This is independent of shape and therefore
deletes every physical Hodge mode.

### `capillary_range_projection:none`

Using raw `s_f` can be correct only if raw `s_f` has already passed N1-N5.  The
current local cut-face curvature cochain has not; previous probes show a
closed-interface residual that is not explained by curvature noise or a
missing continuum multiplier.

### Mean-Curvature Or Null-Mode Calibration

Subtracting a scalar `kappa_bar` can reproduce a continuum formula, but it is
not a proof of:

```text
s_f = -T_h^* d(sigma S_h).
```

It may remain useful as a diagnostic surrogate.  It is production physics only
if it is derived as the discrete constrained variation and shares the same
pressure complex.

### Curvature Smoothing, Caps, Damping, CFL Changes

These do not alter the variational identity.  They can hide or reduce motion,
but they cannot prove that the face cochain is the energy gradient.

### Shape Branching

A rule of the form:

```text
if shape is static benchmark: use range
else: use full cochain
```

is not invariant under reparameterization, topology-preserving deformation,
or perturbation basis.  It cannot represent a variational law.

## 9. Shape-Agnostic Verification Gates

The gates below are the minimum theorem tests.

### G1. Virtual Work Gate

For arbitrary closed interfaces and arbitrary sampled face velocities:

```text
rel_work_error =
| <s_f,w_f>_M + d(sigma S_h)[T_h w_f] |
/ max(|d(sigma S_h)[T_h w_f]|, |<s_f,w_f>_M|, eps)
```

must be near the differentiation/solver tolerance.

### G2. Component Constraint Gate

For every component reaction `b_m`:

```text
||H_R b_m||_M / max(||b_m||_M, eps)
```

must be near tolerance.  If it is not, the augmented complex is mandatory.

### G3. Constrained Criticality Gate

For any discrete constrained critical point found by solving:

```text
dS_h - sum_m mu_m dV_m,h = 0
```

on the trace DOFs:

```text
||H_{R_aug} s_f||_M / max(||s_f||_M, eps)
```

must be near tolerance.

### G4. Noncritical Release Gate

For arbitrary resolved perturbations with nonzero constrained first
variation:

```text
||H_{R_aug} s_f||_M > 0.
```

The perturbation set must include non-elliptic modes, high modes, asymmetric
states, multi-component states, and random resolved trace perturbations.

### G5. Operator Identity Gate

The cochain used in:

```text
D_f s_f, PPE solve, corrector, history, diagnostics
```

must be byte-for-byte or algebraically identical up to intentional pressure
gauge choices.  A diagnostic-only implementation does not pass this gate.

### G6. Reinit Ledger Gate

Every run that reinitializes must report:

```text
S_h(q^n), S_h(q_T), S_h(q^{n+1}),
V_m,h(q^n), V_m,h(q_T), V_m,h(q^{n+1}).
```

The physical capillary ledger uses `q^n -> q_T`; the projection ledger uses
`q_T -> q^{n+1}`.

## 10. Implications For The Current RCA

The previous findings have the following theory status.

1. The direct zero-drive cause is fully explained: replacing `s_f` by
   `Pi_R s_f` makes the applied acceleration zero by algebra.
2. The static closed-interface residual is not a reason to keep range
   projection.  It proves that the current local cochain or pressure range is
   not the closed-interface variational complex.
3. The P2 transport-adjoint tests prove an adjoint identity in their own
   carrier space, but not the full N1-N5 contract in the affine-FCCD pressure
   complex.  This is why P2 can pass local work tests and still fail the
   Hodge/equilibrium gate.
4. The correct fork is not "raw versus projected".  It is:

```text
construct exact s_f and exact b_m in the same complex;
then use the full corrector a_f = Pi_R s_f - s_f.
```

## 11. Concrete Research Tasks Implied By The Theory

These are proof obligations, not implementation-priority tiers.

1. Define the trace DOFs `q` used by ch14 pressure-jump capillarity.
2. Define `S_h(q)` and `V_m,h(q)` on exactly those DOFs.
3. Derive `T_h(q)` from the pre-reinit transport map.
4. Implement or symbolically verify `s_f=-T_h^*d(sigma S_h)`.
5. Implement or verify `b_m=T_h^*dV_m,h`.
6. Measure whether `b_m in range(A_f G_f)` under current affine-FCCD pressure.
7. If not, design the augmented operator `A_f G_f p + B lambda`.
8. Prove the same augmented operator is consumed by PPE, corrector, pressure
   history, HFE representatives, and diagnostics.
9. Add finite-step discrete-gradient closure for non-infinitesimal transport.
10. Keep reinit energy/volume changes in a separate ledger.

## Final Verdict

The physically and mathematically correct target is not any named curvature
formula, projection option, benchmark-specific switch, or schedule-dependent
implementation path.  It is the following closed theorem:

```text
Surface energy:
  s_f = -T_h^* d(sigma S_h)

Component constraints:
  b_m = T_h^* dV_m,h, represented in the same pressure complex

Projection/corrector:
  a_f = Pi_{R_aug} s_f - s_f

Equilibrium:
  H_{R_aug} s_f = 0
  iff q is a discrete constrained critical point

Release:
  H_{R_aug} s_f != 0
  iff the resolved mode has nonzero constrained first variation

Reinit:
  q^n -> q_T supplies capillary work;
  q_T -> q^{n+1} is a separate representation ledger.
```

This is the standard against which every future capillary implementation must
be judged.

[SOLID-X] Theory artifact only; no production solver/config/YAML behavior
changed; no tested implementation deleted; no FD/WENO/PPE fallback introduced.
