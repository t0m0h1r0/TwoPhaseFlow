# SP-AI: Closed-Interface Capillary Discretization Policy

**Status**: ACTIVE / first component-augmented implementation slice
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

## 7. First Implementation Slice

The full fixed-stratum trace/Riesz object remains the final construction.
However, the closed-interface zero-drive RCA exposed a narrower theorem-derived
production slice that is valid to implement before the full trace derivative:
augment the pressure range by the component pressure-jump reaction already
present in the affine-jump complex.

For a single closed component, let `c` be the current capillary jump cochain
and let `b` be the cochain generated by a unit constant pressure jump on the
same cut faces, coefficient field, divergence, PPE solve, and corrector:

```text
h_c = c - Pi_R c,
h_b = b - Pi_R b,
beta = <h_c,h_b>_M / <h_b,h_b>_M,
c_aug = c - beta h_b.
```

Equivalently, this is the one-column case of the augmented projection
`range(A G) + range(B)`, because adding `b` to the range removes only the
Hodge direction `h_b` from the pressure-range complement.  A constant
Young-Laplace component reaction is therefore not applied as acceleration,
while any nonconstant resolved Hodge component orthogonal to `h_b` remains as
physical drive.  This is not a circle/ellipse classifier and not a scalar mean
curvature calibration; it is a projection statement in face-cochain space.

The repository mode is:

```text
capillary_range_projection: component_hodge_augmented
```

Its implementation uses the existing `M_f` diagnostic weights and the same
`D_f,A_f,G_f` affine-jump complex as the production pressure stage.  The
legacy `range_projected` mode remains only for negative controls and static
range diagnostics because it replaces `c` by `Pi_R c` and deletes all Hodge
drive.  The `none` mode remains diagnostic for raw-cochain probes.

The still-open full object is:

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

## 8. N=32, T=1 Implementation Check

The first `component_hodge_augmented` run used the canonical ch14 affine-jump
stack at `N=32,T=1`, with debug diagnostics and 0.2-time snapshot output.

```text
static droplet:
  final KE                         5.284015e-09
  max |Delta V|/V0                 1.903440e-15
  final deformation                0
  max snapshot velocity Linf        1.833331e-05
  max capillary face Linf           9.525267e-05
  max corrected Hodge weighted L2   2.814614e-04

oscillating droplet:
  final KE                         3.643971e-04
  max |Delta V|/V0                 2.428289e-15
  signed deformation               7.617534e-02 -> 4.334637e-02
  max snapshot velocity Linf        9.417805e-03
  max capillary face Linf           1.417884e-02
  max corrected Hodge weighted L2   4.477470e-02
```

Interpretation: the zero-drive theorem failure is removed.  The oscillating
closed interface receives a nonzero corrected Hodge drive instead of the
previous `~1e-37` kinetic energy freeze.  The static droplet is not yet a
roundoff static equilibrium; the residual is small compared with the
oscillating drive but nonzero.  This remaining residual is exactly the reason
the full trace/Riesz cochain `s=-M_f^{-1}T^Td(sigma S_h)^T` is still required:
the current scalar face-implicit curvature cochain is not yet proven to be
the discrete surface-energy gradient.

## 9. Long Validation and Physical Reading

The later N32/T10 and N32/T20 runs answer whether the visually plausible
oscillation should be accepted as physics.  The answer is mixed: the
component-augmented mode fixes the algebraic zero-drive theorem failure, but
the dynamic phase and the reinit coupling are not yet correct enough to close
the capillary-force theory.

Static droplet, reinit disabled, `T=1`:

| N | final KE | max KE | max snapshot speed | max corrected Hodge weighted L2 | max volume drift |
|---:|---:|---:|---:|---:|---:|
| 16 | `1.490637e-07` | `1.490637e-07` | `9.070593e-05` | `8.428385e-04` | `1.223563e-15` |
| 32 | `5.284015e-09` | `5.284015e-09` | `2.492200e-05` | `2.814614e-04` | `1.903440e-15` |
| 64 | `1.138320e-09` | `2.542873e-09` | `1.941430e-05` | `5.893873e-04` | `3.159875e-15` |

The static droplet is volume-stable and nearly still, but the corrected Hodge
residual does not decrease monotonically with resolution.  This blocks any
claim that the current scalar face-implicit curvature cochain is already the
transport-adjoint Riesz representative of surface energy.

Oscillating droplet, `N=32`:

```text
T=10, reinit every step:
  signed deformation              7.617534e-02 -> -2.124984e-02
  Rayleigh-Lamb reference at t=10 -7.874146e-03
  first zero crossing             7.578596
  reference first zero crossing   9.381529
  final/max KE                    2.174340e-03 / 3.512706e-03
  max corrected Hodge L2          9.018738e-02

T=10, reinit disabled:
  signed deformation              7.617534e-02 -> 2.310884e-02
  first zero crossing             none by t=10
  final/max KE                    5.889060e-04 / 6.247928e-04
  max corrected Hodge L2          7.263806e-03

T=20, reinit disabled:
  signed deformation              7.617534e-02 -> -2.228711e-02
  Rayleigh-Lamb reference at t=20 -7.454746e-02
  first zero crossing             13.393564
  reference first zero crossing   9.381529
  final/max KE                    4.117141e-05 / 6.247928e-04
```

Thus the pressure and velocity fields are qualitatively coherent, but the
phase evidence is decisive.  Reinit every step advances the zero crossing and
amplifies energy/Hodge norms; no-reinit dynamics cross too late and are too
damped by `T=20`.  The remedy is not damping, CFL retuning, curvature
smoothing, caps, or another projection of the force into the pressure range.
The remedy is to finish the fixed-stratum virtual-work cochain and to record
the physical transport endpoint separately from the reinit endpoint.

The first implementation slice of that endpoint ledger now stores, at snapshot
steps and checkpoint snapshots,

```text
fields/psi_before_transport,
fields/psi_after_transport_before_reinit,
fields/psi_after_reinit.
```

A remote `N=16,T=0.04` reinit-every-step smoke exported all three fields.  Its
maximum transport-leg change was `6.436583e-07`, while its maximum reinit-leg
change was `1.778247e-01`, directly showing why deformation changes must be
split before they are interpreted as capillary motion.

## 10. Remedy Theory After Phase RCA

The phase RCA rules out two tempting explanations.  The slow no-reinit
oscillation is not caused by the one-component reaction projection removing
the dynamic mode: `capillary_range_projection:none` and
`component_hodge_augmented` give the same early `N=32,T=1` stiffness.  It is
also not an early grid-remap artifact: static-grid and dynamic-grid no-reinit
probes match through the early acceleration window.

The remaining force-side theorem obligation is therefore sharper:

```text
The scalar face_implicit cochain is not the fixed-stratum Riesz
representative of d(sigma S_h).
```

Post-RCA remedy generation considered scalar rescaling, inertia scaling,
damping, CFL reduction, curvature caps, smoothing, raw `none`, restored
`range_projected`, shape-name branching, mean-curvature subtraction, PPE
tolerance changes, component-beta tuning, surface-stress divergence, diffuse
surface-energy derivatives, finite-difference VJPs, analytic transport VJPs,
finite-step discrete gradients, multi-component reaction bases, topology
guards, Rayleigh Hessian gates, and reinit ledgers.  The filter is simple:
surviving candidates must satisfy the same finite-dimensional virtual-work
identity in the same face Hilbert space:

```text
<s,w>_M   = -d(sigma S_h)[T w],
<b_m,w>_M =  dV_m,h[T w],
h         = (I - Pi_X)s,  X=[A_fG_f B].
```

This leaves one coherent remedy family:

```text
1. define S_h and V_m,h on a fixed trace stratum,
2. pull dS_h and dV_m,h back by the actual pre-reinit transport VJP,
3. form s and B as M_f Riesz representatives,
4. remove only pressure and component reactions by the weighted projection,
5. keep full s in the production corrector,
6. record q^n -> q_T separately from q_T -> q^{n+1}.
```

Everything else is diagnostic or rejected as a symptom adjustment.  In
particular, Rayleigh-Lamb is an eigenvalue/Hessian acceptance gate, not a
frequency-fitting source term.  Static droplet validation is a constrained
criticality test of `S_h,V_h`, not a circle detector.  Dynamic validation must
include arbitrary noncritical closed-interface modes, because the method must
compute the quotient capillary force, not identify a named benchmark shape.

## 11. Rigorous Contract Decomposition

The implementation should now be separated into theorem-sized objects.  First,
`ClosedInterfaceStratum` fixes the cut graph, oriented segments, component
labels, host grid edges for trace points, and a topology hash.  With local
edge coordinates `q_i`, trace points satisfy:

```text
x_i(q_i) = (1-q_i)a_i + q_i b_i.
```

All derivatives are conditional on staying inside this stratum.  If a centered
probe changes the topology hash, the derivative is invalid and the path must
fail closed.

Second, `TraceGeometryFunctional` owns the differentiable geometry:

```text
S_h(q) = sum_(i->j) |x_j-x_i|,
V_m,h(q) = C_m(K) + 0.5 sum_(i->j in m) cross(x_i,x_j).
```

For one segment, `d|x_j-x_i| = tau dot (dx_j-dx_i)`.  For one oriented area
edge, `d[0.5 cross(x_i,x_j)] = 0.5 cross(dx_i,x_j)+0.5 cross(x_i,dx_j)`.
This makes curvature an interpretation of `dS_h`, not primitive force data.

Third, `TransportLinearization` owns the actual pre-reinit endpoint map:

```text
q_T = Phi_K(q,u,dt),
T_K = partial_u Phi_K.
```

Its VJP must satisfy `(T_K^T g)^T w = g^T(T_K w)`.  A finite-difference VJP is
acceptable as a diagnostic scaffold only when the stratum hash is unchanged;
production should use an analytic local VJP with the same dot-product gate.

Fourth, `FaceMetricRiesz` defines the cochains:

```text
s = -M_f^{-1}T_K^T d(sigma S_h)^T,
B =  M_f^{-1}T_K^T dV_h^T.
```

Fifth, `AugmentedHodgeProjector` removes only reactions:

```text
X=[A_fG_f B],
h=s-X(X^TM_fX)^+X^TM_f s,
X^TM_fh=0.
```

Rank deficiencies affect coefficients, not the projected vector, so validation
must inspect `h` and the orthogonality residual rather than raw pressure or
component multipliers.  The corrector sign is then fixed by the power gate

```text
d(sigma S_h)[T_K a_cap] = -||h||_M^2
```

to leading order on release from rest.  Finally, the reinit ledger splits:

```text
Delta E_total =
  [E_h(q_T)-E_h(q^n)] + [E_h(q^{n+1})-E_h(q_T)].
```

Only the first bracket is capillary transport work.

## 12. Implementation Method

The implementation should not hide the new law behind the old word
`curvature`.  Keep the public formulation as `pressure_jump`, but add a
capillary source selector:

```yaml
capillary_force:
  formulation: pressure_jump
  source: closed_interface_riesz
```

Then keep the responsibilities separate.  `ClosedInterfaceStratum` owns the
cut topology and hash.  `TraceGeometryFunctional` owns `S_h,V_h,dS_h,dV_h`.
`TransportLinearization` owns the actual pre-reinit VJP.  `CapillaryRieszCochain`
builds `s,B` and reports work residuals.  `AugmentedCapillaryHodgeProjector`
removes only pressure/component reactions.  `CorrectorSignLock` checks energy
power, and `ReinitEnergyLedger` keeps profile projection work separate.

The code should be introduced in proof-sized slices:

```text
1. stratum + geometry finite-difference diagnostics,
2. transport VJP dot-product diagnostics,
3. Riesz cochain work diagnostics,
4. general multi-component augmented projection,
5. explicit experimental runtime mode,
6. ch14 static/dynamic/reinit-separated validation and visuals.
```

The first source commit should stop at slice 1.  It cannot change production
physics, and it locates failures in the geometry layer before PPE signs,
projection rank, or Rayleigh phase are involved.

## Final Policy

The discretization is settled when the solver can state and verify:

```text
s = -M_f^{-1} T^T d(sigma S_h)^T
B =  M_f^{-1} T^T [dV_m]^T
h = s - X (X^T M_f X)^+ X^T M_f s,  X=[A G B]
```

on a fixed trace stratum, with reinit handled by a separate ledger.  This is
the implementation-facing form of the physical law.

[SOLID-X] Theory/design updated for the component-augmented implementation
slice; no tested implementation deleted; no FD/WENO/PPE fallback, damping,
CFL workaround, curvature cap, smoothing, blanket `c -> Pi_R c`, or QP-as-
physics path introduced.
