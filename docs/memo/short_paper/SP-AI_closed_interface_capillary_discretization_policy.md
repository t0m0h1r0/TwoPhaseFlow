# SP-AI: Closed-Interface Capillary Discretization Policy

**Status**: ACTIVE
**Date**: 2026-05-07
**Scope**: ch14 closed-interface capillary force, affine pressure jump, weighted Hodge projection, implementation policy
**Companion papers**: SP-AA, SP-AC, SP-AF, SP-AG

## Abstract

The ch14 oscillating-droplet investigation ruled out two tempting but wrong
answers.  The production replacement `c -> Pi_R c` is algebraically a force
deletion, so it freezes non-equilibrium droplets.  The raw curvature jump
with `capillary_range_projection:none` restores motion, but it is not yet a
theorem-grade surface-energy force because its closed-interface Hodge
component is not proven to be variational.

The correct discretization target is a fixed-stratum, trace-based,
projection-native construction:

```text
s      = -M_f^{-1} T^T d(sigma S_h)^T
B      =  M_f^{-1} T^T [dV_1 ... dV_M]^T
K      = ker D intersection ker(B^T M_f)
R_aug  = K^{perp_M} = range(A G) + range(B)
Pi_aug = M_f-orthogonal projection onto R_aug
h      = s - Pi_aug s
```

The capillary acceleration is the Hodge residual `h` up to the code sign
convention.  The pressure reaction is `Pi_aug s`.  The columns `B` are not a
postprocess; they are component-volume pressure-jump reactions that must share
the PPE, corrector, pressure history, HFE representative, and diagnostics.

This memo records the trial-and-error that led to the discretization policy
and gives an implementation-facing operator plan.

## 1. Non-Negotiable Contract

The method must satisfy the finite-dimensional virtual-work identity:

```text
<s,w>_M + d(sigma S_h)[T w] = 0
```

for arbitrary admissible face velocities `w`, where:

```text
M_f  production face mass/metric
T    pre-reinit face-velocity-to-trace transport differential
S_h  trace surface length/area
V_m  trace volume/area of connected component m
D    production face divergence
R    A G, production pressure acceleration operator
```

Static and dynamic behavior follow from one statement:

```text
h = H_aug s = 0
```

if and only if the trace state is a discrete constrained critical point on the
admissible space:

```text
K = ker D intersection ker(B^T M_f).
```

No production rule may classify shapes by name or choose a different force
law for a named benchmark.

## 2. Trial Log

The following trials were considered while shaping the implementation policy.

### Trial 1: Keep Current Curvature Jump And Use `none`

Idea:

```text
s = current affine cut-face B_Gamma(sigma kappa)
```

and feed the full cochain to the corrector.

Verdict: rejected as final law.

Reason: it moves, but it has not passed the Riesz pullback gate:

```text
s ?= -M_f^{-1} T^T d(sigma S_h)^T.
```

Previous closed-interface probes show a residual that is not curvature noise,
sign error, missing continuum multiplier, or generic PPE failure.  Therefore
`none` is a diagnostic that proves the missing drive; it is not a proof of the
correct force.

### Trial 2: Keep `range_projected`

Idea:

```text
s_prod = Pi_R s.
```

Verdict: rejected.

Reason:

```text
a = Pi_R s_prod - s_prod = 0
```

for zero-predictor capillary release.  This deletes every Hodge component,
including physical noncritical modes.

### Trial 3: Subtract A Scalar Mean Curvature

Idea:

```text
kappa_res = kappa - kappa_bar
s = B_Gamma(sigma kappa_res).
```

Verdict: diagnostic only.

Reason: the continuum constrained-force formula is not enough.  The scalar
`kappa_bar` is physical only if it arises from the same discrete constrained
variation and the omitted component reaction is represented in the pressure
complex.  Otherwise it is a calibrated residual fit.

### Trial 4: Exact-Lift Every Jump Into Pressure Range

Idea:

```text
s = A G q_lift
```

for all jump content.

Verdict: rejected.

Reason: it makes all capillarity pressure range.  The Hodge residual then
vanishes for both constrained critical and noncritical modes.  This is a force
deletion in another notation.

### Trial 5: Use Existing P2 Carrier Variational Gradient

Idea: reuse the current transport-adjoint/P2 surface-energy gradient.

Verdict: rejected as production pressure-jump physics.

Reason: the P2 route can satisfy a work identity in its own carrier space but
still fail the affine-FCCD weighted Hodge/equilibrium gate.  The missing step
is not "more variational words"; it is equality in the same `M_f,D,R`
pressure complex.

### Trial 6: Add Component DOFs To PPE But Keep Raw Curvature `s`

Idea:

```text
R_aug = range(A G) + range(B),
h = H_aug s_raw.
```

Verdict: useful intermediate diagnostic, insufficient final law.

Reason: component reactions can fix missing volume-pressure modes, but they
cannot make a nonvariational `s_raw` into `-T^T dS`.  Both sides are required:
the surface covector `s` and the component reactions `B` must come from the
same trace geometry.

### Trial 7: Trace Polygon With Exact Shape Derivatives

Idea: define the interface trace as a fixed-stratum polygon/cut graph, compute
`S_h` and `V_m`, differentiate them exactly, and pull the derivatives back to
faces through the pre-reinit transport Jacobian.

Verdict: selected.

Reason: this is the first trial that gives every object from one finite
dimensional variational diagram:

```text
face velocity -> trace displacement -> dS_h and dV_m -> face cochain.
```

It does not need curvature as primitive data.  Curvature may be reconstructed
later as an interpretation of `dS_h`, but not as the force definition.

### Trial 8: Solve Only The Augmented Divergence Equation

Idea:

```text
D(Rp + Bmu) = D s.
```

Verdict: incomplete.

Reason: this enforces divergence matching, but the `M_f` projection also
requires:

```text
B^T M_f (Rp + Bmu - s) = 0.
```

Without this side condition, the projection is oblique or underdetermined
unless `B` is already redundant with `range(R)`.

### Trial 9: Full Weighted Normal Equations

Idea:

```text
X = [R B],
X^T M_f X z = X^T M_f s.
```

Verdict: selected projection definition.

Reason: this is exactly the `M_f`-orthogonal projection onto the pressure plus
component-reaction space.  It is also compatible with an implementation using
existing PPE solves through a small Schur complement for component reactions.

### Trial 10: Finite-Step Discrete Gradient

Idea: replace infinitesimal `dS_h` and `dV_m` by finite-step discrete
gradients satisfying exact energy differences.

Verdict: required for production energy ledgers, but the infinitesimal version
is sufficient for first diagnostic construction and one-step acceleration
gates.

Reason: first-step release from rest uses the infinitesimal covector.  A
longer physical energy claim needs:

```text
bar_g_S^T Delta q = S_h(q_T) - S_h(q^n).
```

Both use the same trace geometry and face metric.

## 3. Settled Discretization Policy

The implementation must start with fixed-topology trace geometry, not with a
curvature formula.

### 3.1 Trace Stratum

Create a stratum object containing:

```text
component labels,
crossing edges,
cut points,
polygon adjacency,
orientation,
stratum id.
```

The stratum is valid only while no crossing pattern or component label
changes.  A topology change is a separate event, not a capillary force.

### 3.2 Geometry Functionals

On that stratum define:

```text
S_h(q)    = sum polygon edge lengths,
V_m,h(q) = oriented area/volume of component m.
```

For a polygon with vertices `x_i`:

```text
dS_h[delta x] =
  sum_i (tau_{i-1} - tau_i) dot delta x_i,

dV_h[delta x] =
  1/2 sum_i J_perp(x_{i+1} - x_{i-1}) dot delta x_i.
```

These are the primary geometry derivatives.  Any curvature array must be
validated as a derived representation of this derivative.

### 3.3 Transport Differential

For a cut point on a carrier edge:

```text
theta = (eta - psi_a) / (psi_b - psi_a),
x_cut = x_a + theta (x_b - x_a).
```

On a fixed crossing stratum:

```text
delta x_cut = (x_b - x_a) delta theta,
delta psi   = -dt D_f(P_f psi^theta w_f).
```

Thus:

```text
T w_f = (d x_cut / d psi) [-dt D_f(P_f psi^theta w_f)].
```

This chain rule is the bridge from face velocity to trace displacement.

### 3.4 Face Riesz Pullback

Use the production face metric:

```text
||x||_M^2 = x^T M_f x.
```

Build:

```text
s = -M_f^{-1} T^T d(sigma S_h)^T,
B =  M_f^{-1} T^T [dV_1 ... dV_M]^T.
```

Do not build `s` by multiplying curvature samples by cut-face masks unless
that cochain is proven equal to this Riesz pullback.

### 3.5 SBP And Projection

Verify:

```text
<R p,w>_M + <p,Dw>_C = boundary(p,w).
```

Only then can the PPE divergence solve be read as a weighted Hodge projection.
The augmented projection is:

```text
X=[R B],
Pi_aug s = X (X^T M_f X)^+ X^T M_f s,
h = s - Pi_aug s.
```

The production acceleration is `h` up to sign convention.

## 4. Solver-Oriented Projection Plan

The full normal equation is too large to assemble naively, but the component
part is small.  Use existing PPE solves to form a Schur complement.

Let:

```text
L = D R,
C = D B,
r = D s.
```

For a trial component coefficient `mu`:

```text
p(mu) = L^+ (r - C mu),
q(mu) = R p(mu) + B mu - s.
```

The missing normal-equation condition is:

```text
B^T M_f q(mu) = 0.
```

This gives a small dense system:

```text
S_B mu = y_B,

S_B = B^T M_f [B - R L^+ C],
y_B = B^T M_f [s - R L^+ r].
```

After solving for `mu`:

```text
p = L^+ (r - C mu),
h = s - R p - B mu.
```

This plan preserves the current PPE machinery while adding the mathematically
necessary component orthogonality.  It is not a fallback and not a QP
reinterpretation; it is the projected normal equation reduced to the small
component subspace.

## 5. Implementation Staging As Proof Obligations

The order below is not a near/mid/long-term correctness hierarchy.  It is the
logical dependency graph.

### Obligation A: Fixed-Stratum Diagnostics

Implement diagnostic-only construction of:

```text
q, S_h, V_m, T, M_f, s, B.
```

Pass:

```text
<s,w>_M + d(sigma S_h)[T w] = 0,
<b_m,w>_M - dV_m[T w] = 0.
```

### Obligation B: Projection Equivalence

Assemble or matrix-free evaluate:

```text
h_normal = s - X (X^T M_f X)^+ X^T M_f s.
```

Compare with the PPE/corrector residual.  They must match.

### Obligation C: Component Rank Decision

Measure:

```text
||H_R b_m||_M / ||b_m||_M.
```

If it is near tolerance for all independent components, no component
augmentation is needed for that stratum.  If not, `B` must enter the projection
operator.

### Obligation D: Production Corrector

Only after A-C pass, feed the full theorem-grade cochain through:

```text
a = Pi_aug s - s
```

with the same history and HFE representative.

### Obligation E: Finite-Step Energy Ledger

For finite transport:

```text
bar_g_S^T Delta q = Delta S_h,
bar_g_V^T Delta q = Delta V_h.
```

Use the same `M_f` and projection structure for the discrete-gradient cochain.

### Obligation F: Reinit Separation

Report:

```text
S_h(q^n), S_h(q_T), S_h(q^{n+1}),
V_m(q^n), V_m(q_T), V_m(q^{n+1}),
stratum id before/after reinit.
```

Only `q^n -> q_T` is reversible capillary work.

## 6. What To Avoid During Implementation

The following are explicitly outside the selected policy:

```text
curvature cap,
curvature smoothing as force repair,
damping or CFL reduction as capillary fix,
FD/WENO/PPE fallback,
benchmark-name branch,
blanket range projection,
raw full cochain without Riesz pullback proof,
component DOF added only to diagnostics,
divergence-only augmented solve without B^T M_f side conditions.
```

## 7. Current Implementation Target

The first code design should expose a diagnostic object, not alter production
behavior:

```text
ClosedInterfaceStratum
  cut points
  component polygons
  S_h, V_m,h
  dS_h, dV_m,h
  transport VJP: T^T g

CapillaryVariationalCochain
  M_f
  s
  B
  Riesz work residuals
  component range residuals
  normal-equation projection residuals
```

Once the diagnostic object passes the gates, the same object can become the
production source for the affine pressure-jump PPE/corrector.

## Final Policy

The discretization is settled when the solver can state and verify:

```text
s = -M_f^{-1} T^T d(sigma S_h)^T
B =  M_f^{-1} T^T [dV_m]^T
h = s - X (X^T M_f X)^+ X^T M_f s,  X=[A G B]
```

on a fixed trace stratum, with reinit handled by a separate ledger.  This is
the implementation-facing form of the physical law.

[SOLID-X] Theory/design short paper only; no production solver/config/YAML
behavior changed; no tested implementation deleted; no FD/WENO/PPE fallback
introduced.
