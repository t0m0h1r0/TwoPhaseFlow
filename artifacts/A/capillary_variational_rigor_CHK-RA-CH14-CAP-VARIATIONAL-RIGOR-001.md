# CHK-RA-CH14-CAP-VARIATIONAL-RIGOR-001 - Rigorous Finite-Dimensional Capillary Variational Theory

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`

## Purpose

`CHK-RA-CH14-CAP-VARIATIONAL-THEORY-001` selected the correct principle:
capillarity must be the face-space pullback of discrete surface-energy
virtual work in the same PPE/corrector complex.  This note makes that
principle algebraically precise.

The key refinement is that an augmented pressure/jump complex cannot be
specified only by adding columns to the PPE divergence equation.  It must also
define the weighted orthogonal projection, the admissible velocity subspace,
the component-volume reaction equations, gauges, and rank conditions.  Without
those details, a proposed theory can still hide a range-projection patch under
new notation.

## 1. Pairings And Riesz Representatives

All statements are finite-dimensional and are made on one fixed topology
stratum.

```text
F_h       face velocity/acceleration coordinate space
P_h       pressure coordinate space
C_h       cell divergence coordinate space
Q_h       trace/interface coordinate space
M_f       symmetric positive definite face mass/metric
M_c       cell mass/volume metric
D         D_f: F_h -> C_h
G         G_f: P_h -> face-gradient coordinates
A         A_f: face inverse-density/coefficient map
R         A G: P_h -> F_h
```

Face cochains are represented by their `M_f`-Riesz representatives.  Thus a
linear functional `ell in F_h^*` is represented by the unique vector `s in F_h`
such that:

```text
ell(w) = <s,w>_M = s^T M_f w.
```

This matters because the transport pullback is a dual-space object.  If
`g_E = d_q E_h(q)` is a row/dual vector on `Q_h` and
`T = T_h(q): F_h -> T_q Q_h`, then the face representative of capillary work is:

```text
s = - M_f^{-1} T^T g_E^T.
```

Similarly, for component volume `V_m,h`:

```text
b_m = M_f^{-1} T^T g_{V_m}^T.
```

The shorthand `s=-T_h^*dE` and `b_m=T_h^*dV_m` is therefore always understood
as this Riesz-represented pullback in the production face metric.

## 2. SBP Compatibility And The Pressure Range

The pressure acceleration range is:

```text
R_h = range(R),        R = A G.
```

For the PPE split to be an `M_f` Hodge split, the production operators must
satisfy the summation-by-parts compatibility:

```text
<R p, w>_M = - <p, D w>_C + boundary(p,w)
```

for all pressure coordinates `p` and admissible face velocities `w`.  In
periodic or compatible wall-boundary tests the boundary term is zero or is
absorbed by the declared boundary condition.  Algebraically:

```text
R^T M_f = - M_c D       on the admissible boundary subspace.
```

When this holds:

```text
R_h^{perp_M} = ker D
```

modulo pressure gauges and boundary constraints.  This is the precise
condition under which solving:

```text
D R p = D s
```

is equivalent to the weighted projection of `s` onto `range(R)`.  If SBP fails,
`D R p = D s` may still make the residual divergence-free, but it is no
longer the theorem-grade `M_f` orthogonal Hodge projection.

## 3. Component Volumes And The Admissible Subspace

Let there be `M` closed interface components on the current stratum.  Define:

```text
B = [b_1 ... b_M],    b_m = M_f^{-1} T^T dV_m^T.
```

The physically admissible velocity space is not "all non-pressure modes"; it
is the space that preserves both cell incompressibility and the represented
component volumes:

```text
K = { w in F_h :
        D w = 0,
        B^T M_f w = 0,
        w satisfies boundary conditions }.
```

Here:

```text
B^T M_f w = [dV_1(Tw), ..., dV_M(Tw)]^T.
```

If discrete incompressibility already implies the component volume equations,
then the columns of `B` are redundant with `range(R)`.  If not, the component
volume reactions are missing pressure/jump modes and must be represented
explicitly.

The reaction space is the weighted annihilator of `K`:

```text
R_aug = K^{perp_M}.
```

Under SBP and finite-dimensional closed range:

```text
R_aug = range(R) + range(B),
```

after removing linearly dependent or gauge-null columns.

## 4. The Correct Projection Problem

Let:

```text
X = [R B].
```

The capillary reaction part is the weighted least-squares projection:

```text
z_* = argmin_z 1/2 ||s - X z||_M^2,
Pi_aug s = X z_*,
h = H_aug s = s - Pi_aug s.
```

The normal equations are:

```text
X^T M_f X z = X^T M_f s.
```

Written by blocks:

```text
[ R^T M_f R   R^T M_f B ] [p ] = [ R^T M_f s ]
[ B^T M_f R   B^T M_f B ] [mu]   [ B^T M_f s ].
```

The pressure block is equivalent to divergence matching only under the SBP
identity:

```text
D(Xz - s) = 0.
```

The component block is the extra condition that a pure component-volume
reaction performs no work on the final Hodge velocity:

```text
B^T M_f (Xz - s) = 0.
```

Therefore an augmented theory that solves only:

```text
D(Rp + Bmu) = D s
```

is underdetermined or oblique unless it also supplies the `B^T M_f` side
conditions or proves they are redundant.  This is the main algebraic
tightening relative to the previous artifact.

The velocity-driving Hodge cochain is `h`.  The existing face-history code may
store the opposite sign:

```text
a_code = Pi_aug s - s = -h.
```

The invariant statement is the work identity:

```text
<h,w>_M = <s,w>_M
```

for every `w in K`.

## 5. Gauges, Rank, And LICQ

The projection is unique if `X` has full column rank after gauges are removed.
In practice:

1. constant pressure gauges must be removed from `P_h`;
2. component reaction columns that already lie in `range(R)` must be removed
   or orthogonalized;
3. disconnected components with redundant volume equations must be reduced to
   an independent set;
4. topology-stratum changes invalidate the rank decision.

The rigorous condition is:

```text
rank(X) = dim(range(R) + range(B)).
```

Equivalently, the Gram matrix:

```text
G_X = X^T M_f X
```

must be nonsingular on the gauge-reduced coordinates.  If it is singular, the
Moore-Penrose projection is still definable, but the null directions must be
reported because they indicate either gauge freedom or missing constraints.

The component constraint gradients satisfy a discrete LICQ condition on the
transport image:

```text
rank( B^T M_f |_{ker D} ) = number of independent component volumes.
```

If LICQ fails, the multipliers are not unique.  The Hodge drive may still be
unique, but pressure-jump interpretation is not.

## 6. Shape Functional Derivatives

The theory requires the exact derivative of the chosen `S_h` and `V_m,h`.
Curvature is allowed only as a consequence of this derivative, not as an
independent substitute.

### 6.1 Polygonal Trace

For a closed oriented polygon with vertices `x_i` and edges:

```text
e_i = x_{i+1} - x_i,
l_i = ||e_i||,
tau_i = e_i / l_i,
S_h = sum_i l_i,
V_h = 1/2 sum_i cross(x_i, x_{i+1}),
```

on a fixed nondegenerate stratum `l_i>0`, the variations are:

```text
dS_h[delta x]
  = sum_i (tau_{i-1} - tau_i) . delta x_i,

dV_h[delta x]
  = 1/2 sum_i J_perp(x_{i+1} - x_{i-1}) . delta x_i,
```

where `J_perp` is the orientation-dependent ninety-degree rotation consistent
with the chosen signed area convention.

Thus the polygonal surface covector is a vertex force.  It is not a pointwise
curvature sample.  The raw curvature route is valid only if its face cochain
is algebraically equal to the Riesz pullback of this vertex covector.

### 6.2 Cut-Cell Or Marching-Squares Trace

For a cut point on an edge with endpoint carrier values `psi_a, psi_b` and
threshold `eta`:

```text
theta = (eta - psi_a) / (psi_b - psi_a),
x_cut = x_a + theta (x_b - x_a).
```

On a fixed crossing stratum `psi_a != psi_b` and no sign changes in the
crossing pattern:

```text
delta theta =
  ((eta - psi_b) delta psi_a + (psi_a - eta) delta psi_b)
  / (psi_b - psi_a)^2,

delta x_cut = (x_b - x_a) delta theta.
```

The carrier perturbation comes from pre-reinit transport:

```text
delta psi = T_psi w = -dt D_f(P_f psi^theta w).
```

Therefore:

```text
T_h w = (d x_cut / d psi) T_psi w,
s = -M_f^{-1} T_h^T d(sigma S_h)^T,
b_m = M_f^{-1} T_h^T dV_m,h^T.
```

This is the precise chain rule that current diffuse or P2 carrier-gradient
tests must satisfy before they can be pressure-jump physics.

### 6.3 Non-Smooth Strata

If a cut pattern changes, an edge length vanishes, components merge/split, or
the trace self-intersects, `S_h` and `V_m,h` can become non-differentiable.
Such a step is not reversible capillary motion in this theorem.  It must be
handled as:

```text
fixed-stratum rejection,
declared topology event,
or metric/topology dissipation ledger.
```

It cannot be silently absorbed into a capillary force.

## 7. The Refined Main Theorem

### Theorem

Assume all of the following on a fixed topology stratum:

1. `S_h` and all independent `V_m,h` are differentiable on `Q_h`.
2. `T: F_h -> T_q Q_h` is the differential of the pre-reinit transport.
3. `s=-M_f^{-1}T^Td(sigma S_h)^T` and `B=M_f^{-1}T^T[dV_m]^T`.
4. SBP holds: `<Rp,w>_M = -<p,Dw>_C` on the admissible boundary subspace.
5. `R_aug = range(R)+range(B)` after gauge/rank reduction.
6. `Pi_aug` is the `M_f`-orthogonal projection onto `R_aug`.

Then:

```text
h = H_aug s
```

is the unique `M_f`-Riesz representative of the negative constrained
surface-energy first variation on:

```text
K = ker D intersection ker(B^T M_f).
```

Equivalently, for every `w in K`:

```text
<h,w>_M = -d(sigma S_h)[T w].
```

Consequently:

```text
h = 0
```

if and only if:

```text
d(sigma S_h)[T w] = 0    for every w in K.
```

And:

```text
h != 0
```

if and only if there exists a resolved admissible velocity `w in K` such that:

```text
d(sigma S_h)[T w] != 0.
```

This is the shape-agnostic static/dynamic criterion.

### Proof

Because `Pi_aug` is the `M_f` projection onto `R_aug`, the residual:

```text
h = s - Pi_aug s
```

lies in:

```text
K = R_aug^{perp_M}.
```

For any `w in K`, the projected part does no work:

```text
<Pi_aug s, w>_M = 0.
```

Therefore:

```text
<h,w>_M = <s,w>_M.
```

By the Riesz pullback definition of `s`:

```text
<s,w>_M = -d(sigma S_h)[T w].
```

This proves the work identity.  If `h=0`, the left side is zero for all
`w in K`, so the constrained first variation is zero on all admissible
transport directions.  Conversely, if the constrained first variation is zero
on all `K`, then `<s,w>_M=0` for all `w in K`, so `s in K^{perp_M}=R_aug`, and
therefore `H_aug s=0`.

The noncritical statement is the contrapositive plus the finite-dimensional
Riesz theorem on `K`.

## 8. Relation To Lagrange Multipliers

The constrained functional form:

```text
E_lambda(q) = sigma S_h(q) - sum_m lambda_m V_m,h(q)
```

gives the residual face representative:

```text
s_lambda = -M_f^{-1}T^T dE_lambda^T
         = s + sum_m lambda_m b_m.
```

This eliminated form is equivalent to the augmented projection only when the
`b_m` columns are represented in the same pressure/reaction space and the
chosen `lambda_m` are those selected by the projection equations.  With
`X=[R B]`, the block solve gives coefficients `(p,mu)` in:

```text
Pi_aug s = R p + B mu.
```

The eliminated multiplier is `lambda=-mu` under the sign convention above:

```text
h = s - R p - B mu = s_lambda - R p.
```

Thus a scalar `lambda` computed from a curvature average is not sufficient.
It must be the multiplier that closes the same weighted projection problem, or
it is a tuning parameter.

## 9. Finite-Step Discrete Gradient

For non-infinitesimal transport, replace `dS_h` by a discrete gradient
`bar_g_S` satisfying:

```text
bar_g_S^T Delta q = S_h(q_T) - S_h(q^n).
```

Likewise, for each component:

```text
bar_g_{V_m}^T Delta q = V_m,h(q_T) - V_m,h(q^n).
```

Let `bar_T` be the transport increment map that relates a face displacement
`Delta x_f` to the trace increment `Delta q`.  The finite-step Riesz
representatives are:

```text
bar_s = -M_f^{-1} bar_T^T (sigma bar_g_S),
bar_b_m = M_f^{-1} bar_T^T bar_g_{V_m}.
```

The finite-step projection uses:

```text
bar_X = [R_bar  bar_B],
bar_h = H_{bar_X} bar_s.
```

Then for any finite-step displacement represented in the admissible subspace:

```text
<bar_h, Delta x_f>_M
  = -sigma [S_h(q_T) - S_h(q^n)].
```

If the method is coupled to component constraints:

```text
<bar_h, Delta x_f>_M
  = -[sigma Delta S_h - sum_m lambda_bar_m Delta V_m,h].
```

A Gonzalez correction is mathematically admissible only if it preserves this
identity in the same `M_f` metric and does not add a component outside the
transport increment direction.  A correction computed in carrier Euclidean
norm but consumed in face `M_f` norm is not a proof.

## 10. Reinitialization And Stratum Accounting

The theorem applies to:

```text
q^n -> q_T.
```

For:

```text
q_T -> q^{n+1} = Pi_h(q_T),
```

there are three possibilities.

1. Trace-preserving projection:

```text
S_h(q^{n+1}) = S_h(q_T),
V_m,h(q^{n+1}) = V_m,h(q_T).
```

Then the capillary ledger is unchanged.

2. Metric projection with declared dissipation:

```text
Delta S_Pi, Delta V_Pi
```

are reported and charged to a named metric budget, not to reversible
capillary work.

3. Topology-stratum event:

component count, crossing pattern, or differentiability changes.  The
fixed-stratum theorem stops at `q_T`, and the event must be accepted or
rejected by a separate topology policy.

## 11. Strong Verification Gates

The following gates are stricter than the previous artifact.

### G1. Riesz Pullback Gate

For random face velocities `w`:

```text
rel =
| <s,w>_M + d(sigma S_h)[T w] |
/ max(|<s,w>_M|, |d(sigma S_h)[T w]|, eps)
```

must be near tolerance.  Repeat for each `b_m`:

```text
| <b_m,w>_M - dV_m[T w] |.
```

### G2. SBP Gate

For random pressure `p` and admissible face velocity `w`:

```text
<R p,w>_M + <p,Dw>_C - boundary(p,w)
```

must be near tolerance.  This verifies that the PPE divergence solve is the
weighted Hodge projection claimed by the theory.

### G3. Projection Equivalence Gate

Compare:

```text
h_normal = s - X (X^T M_f X)^+ X^T M_f s
```

with the implemented PPE/corrector residual.  They must match in `M_f` norm.
If the implementation uses only `D X z = D s`, this gate detects missing
component orthogonality.

### G4. Component Rank Gate

Compute ranks and condition numbers of:

```text
R, B, X=[R B], G_X=X^T M_f X,
B^T M_f restricted to ker D.
```

Report redundant component reactions and pressure gauges explicitly.

### G5. Fixed-Stratum Shape-Derivative Gate

For polygonal/cut traces, perturb trace DOFs without changing crossing
pattern or component labels.  Verify:

```text
dS_h, dV_m,h
```

against centered finite differences over an epsilon sweep.

### G6. Noncritical Completeness Gate

Sample admissible velocities from `K`.  Whenever:

```text
dS_h[T w] != 0,
```

verify:

```text
<h,w>_M != 0
```

with the predicted sign.  The sample set must include arbitrary resolved
modes, not named benchmark modes.

### G7. Finite-Step Gate

For finite transport increments:

```text
<bar_s, Delta x_f>_M + sigma Delta S_h = 0
```

and the corresponding component-volume identities must hold before any
production energy claim is made.

### G8. Reinit Stratum Gate

Report:

```text
S_h(q^n), S_h(q_T), S_h(q^{n+1}),
V_m,h(q^n), V_m,h(q_T), V_m,h(q^{n+1}),
component labels,
crossing-stratum id.
```

The physical capillary theorem is evaluated only on the first arrow.

## 12. Consequences For Future Implementation

The next implementation should not begin by choosing a curvature formula.  It
should begin by constructing these matrices and covectors on a fixed stratum:

```text
M_f, D, R=A G, T, dS_h, dV_m,h, s, B.
```

Then it must answer, in order:

1. Does `s` pass the Riesz pullback gate?
2. Does `R` pass the SBP gate with the production divergence?
3. Are all independent `b_m` already in `range(R)`?
4. If not, does `X=[R B]` have a well-conditioned gauge-reduced projection?
5. Does the implemented PPE/corrector residual equal the normal-equation
   projection residual?
6. Do fixed-stratum critical states give `h=0` without shape classifiers?
7. Do arbitrary resolved noncritical modes give `h!=0`?

Only after these are true does using the full capillary cochain in production
become physically and mathematically justified.

## Final Rigorous Statement

The theorem-grade pressure-jump capillary method is the following finite
dimensional construction:

```text
s      = -M_f^{-1} T^T d(sigma S_h)^T
B      =  M_f^{-1} T^T [dV_1 ... dV_M]^T
K      = ker D intersection ker(B^T M_f)
R_aug  = K^{perp_M} = range(A G) + range(B)
Pi_aug = M_f-orthogonal projection onto R_aug
h      = s - Pi_aug s
```

with gauges and redundant volume reactions removed.

Then:

```text
<h,w>_M = -d(sigma S_h)[T w]    for every w in K,
```

and therefore:

```text
h = 0
```

is exactly discrete constrained criticality as represented by the solver, and:

```text
h != 0
```

is exactly nonzero constrained capillary release on a resolved admissible
mode.

Anything that does not instantiate this construction is not yet the physical
surface-tension law.  It is either a diagnostic, an approximation requiring a
proof of equivalence, or a non-fix.

[SOLID-X] Theory artifact only; no production solver/config/YAML behavior
changed; no tested implementation deleted; no FD/WENO/PPE fallback introduced.
